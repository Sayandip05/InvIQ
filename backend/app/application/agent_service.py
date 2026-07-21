"""
LangGraph AI Agent Service.

Creates a ReAct agent powered by Groq LLM that can query inventory data
using the 7 existing @tool functions. Falls back to rule-based responses
when GROQ_API_KEY is not configured.

Architecture:
    chat.py → agent_service.invoke() → LangGraph ReAct → @tool functions → DB
"""

import concurrent.futures
import contextvars
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
    get_near_expiry_items,
    get_cold_chain_items,
)

logger = logging.getLogger("smart_inventory.agent")

# ── All 9 inventory tools (7 core + 2 pharmacy-specific) ──────────────────────
INVENTORY_TOOLS = [
    get_inventory_overview,
    get_critical_items,
    get_stock_health,
    calculate_reorder_suggestions,
    get_location_summary,
    get_category_analysis,
    get_consumption_trends,
    get_near_expiry_items,
    get_cold_chain_items,
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
        _agent = None
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
    global _agent, _agent_available

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
        # Cross-platform 30-second timeout using a thread pool future.
        # signal.SIGALRM is not available on Windows and is therefore useless here.
        #
        # CRITICAL: contextvars (including the DB session ContextVar set by
        # set_db_session() in chat.py) are NOT automatically inherited by worker
        # threads in Python <3.12.  We must capture the current context snapshot
        # with copy_context() and then run the agent inside that snapshot using
        # ctx.run(), otherwise _get_db() returns None inside every @tool function.
        ctx = contextvars.copy_context()

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(ctx.run, _agent.invoke, {"messages": messages})
            try:
                result = future.result(timeout=30)
            except concurrent.futures.TimeoutError:
                logger.error("Agent invocation timed out after 30s")
                raise RuntimeError("Agent request timed out — please try again")

        # Extract the final assistant message from the agent response.
        agent_messages = result.get("messages", [])

        # Walk backwards to find the last AI message that is not a tool call.
        for msg in reversed(agent_messages):
            content = getattr(msg, "content", None)
            if not content:
                continue
            tool_calls = getattr(msg, "tool_calls", None)
            if not tool_calls:
                return content

        # Fallback: return the last message content if it has any.
        if agent_messages:
            last_content = getattr(agent_messages[-1], "content", None)
            return last_content or "I couldn't generate a response. Please try rephrasing."

        return "I couldn't generate a response. Please try rephrasing your question."

    except RuntimeError:
        raise
    except Exception as e:
        # Detect Groq 401 / expired key — reset the singleton so the next
        # request rebuilds the agent with the current key from settings.
        err_str = str(e)
        if "401" in err_str or "invalid_api_key" in err_str or "expired_api_key" in err_str or "AuthenticationError" in type(e).__name__:
            _agent = None
            _agent_available = False
            logger.warning(
                "Groq API key rejected (401) — agent reset. Update GROQ_API_KEY and retry."
            )
            raise RuntimeError("Groq API key is invalid or expired — please update GROQ_API_KEY")
        logger.error("Agent invocation failed: %s", e, exc_info=True)
        raise RuntimeError(f"Agent error: {str(e)}")
