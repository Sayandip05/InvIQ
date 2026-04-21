"""
LangGraph AI Agent Service.

Creates a ReAct agent powered by Groq LLM that can query inventory data
using the 7 existing @tool functions. Falls back to rule-based responses
when GROQ_API_KEY is not configured.

Architecture:
    chat.py → agent_service.invoke() → LangGraph ReAct → @tool functions → DB
"""

import logging
from typing import Optional
from datetime import datetime

from app.core.config import settings
from app.domain.agent.prompts import get_system_prompt
from app.application.agent_tools import (
    get_inventory_overview,
    get_critical_items,
    get_stock_health,
    calculate_reorder_suggestions,
    get_location_summary,
    get_category_analysis,
    get_consumption_trends,
)

logger = logging.getLogger("smart_inventory.agent")

# ── All 7 inventory tools ──────────────────────────────────────────────────
INVENTORY_TOOLS = [
    get_inventory_overview,
    get_critical_items,
    get_stock_health,
    calculate_reorder_suggestions,
    get_location_summary,
    get_category_analysis,
    get_consumption_trends,
]

# ── Lazy-initialized agent singleton ───────────────────────────────────────
_agent = None
_agent_available = False


def _build_agent():
    """Build the LangGraph ReAct agent. Called once on first use."""
    global _agent, _agent_available

    if not settings.GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set — LLM agent disabled, using rule-based fallback")
        _agent_available = False
        return

    try:
        from langchain_groq import ChatGroq
        from langgraph.prebuilt import create_react_agent

        llm = ChatGroq(
            model=settings.LLM_MODEL,
            api_key=settings.GROQ_API_KEY,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )

        _agent = create_react_agent(
            model=llm,
            tools=INVENTORY_TOOLS,
        )
        _agent_available = True
        logger.info(
            "LangGraph ReAct agent initialized (model: %s, temp: %.1f, max_tokens: %d)",
            settings.LLM_MODEL,
            settings.LLM_TEMPERATURE,
            settings.LLM_MAX_TOKENS
        )

    except Exception as e:
        logger.error("Failed to initialize LangGraph agent: %s", e)
        _agent_available = False


def is_agent_available() -> bool:
    """Check if the LLM agent is ready."""
    global _agent
    if _agent is None and settings.GROQ_API_KEY:
        _build_agent()
    return _agent_available


def invoke_agent(
    question: str,
    conversation_history: list[dict] = None,
    vector_context: str = "",
) -> str:
    """
    Run the LangGraph ReAct agent on a user question.

    Args:
        question: The user's natural language query
        conversation_history: List of {"role": ..., "content": ...} dicts
        vector_context: Relevant past context from ChromaDB

    Returns:
        The agent's text response

    Raises:
        RuntimeError: If agent is not available (caller should fallback)
    """
    global _agent

    if not is_agent_available():
        raise RuntimeError("LLM agent not available")

    # Build the system prompt with current time + past context
    system_prompt = get_system_prompt(
        current_date=datetime.now(),
        past_context=vector_context if vector_context else None,
    )

    # Build message list: system → history → current question
    messages = [{"role": "system", "content": system_prompt}]

    if conversation_history:
        # Include last 6 messages for continuity (avoid token overflow)
        for msg in conversation_history[-6:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

    messages.append({"role": "user", "content": question})

    try:
        result = _agent.invoke({"messages": messages})

        # Extract the final assistant message from the agent response
        agent_messages = result.get("messages", [])

        # Walk backwards to find the last AI message (not a tool call)
        for msg in reversed(agent_messages):
            if hasattr(msg, "content") and msg.content and not hasattr(msg, "tool_calls"):
                return msg.content
            # Handle messages with content but empty tool_calls
            if hasattr(msg, "content") and msg.content:
                tool_calls = getattr(msg, "tool_calls", None)
                if not tool_calls:
                    return msg.content

        # Fallback: return last message content if available
        if agent_messages and hasattr(agent_messages[-1], "content"):
            return agent_messages[-1].content or "I couldn't generate a response. Please try rephrasing."

        return "I couldn't generate a response. Please try rephrasing your question."

    except Exception as e:
        logger.error("Agent invocation failed: %s", e, exc_info=True)
        raise RuntimeError(f"Agent error: {str(e)}")
