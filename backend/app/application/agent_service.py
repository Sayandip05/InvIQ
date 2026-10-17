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
from app.application.agent_prompts import get_system_prompt
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
    search_medicines,
)

logger = logging.getLogger("smart_inventory.agent")

# All 10 inventory tools (7 core + 3 pharmacy-specific)
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
    search_medicines,
]


# Lazy-initialized agent singleton
_agent = None
_agent_available = False
_agent_executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)



def _build_agent():
    """Build the LangGraph ReAct agent. Called once on first use."""
    global _agent, _agent_available

    if not settings.GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set — LLM agent disabled, using rule-based fallback")
        _agent_available = False
        return

    try:
        import os
        from langchain_groq import ChatGroq
        from langgraph.prebuilt import create_react_agent

        # Push LangSmith settings into os.environ for LangChain/LangGraph telemetry
        if settings.LANGCHAIN_TRACING_V2 and settings.LANGCHAIN_TRACING_V2.lower() == "true" and settings.LANGCHAIN_API_KEY:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
            os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
            os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGCHAIN_ENDPOINT
            logger.info("LangSmith tracing active for project '%s'", settings.LANGCHAIN_PROJECT)

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
    admin_name: str = None,
    pharmacy_name: str = None,
    primary_counter: str = None,
    has_inventory: bool = True,
) -> str:
    """
    Run the LangGraph ReAct agent on a user question.

    Args:
        question: The user's natural language query
        conversation_history: List of {"role": ..., "content": ...} dicts
        vector_context: Relevant past context from Vector DB
        admin_name: Name of the pharmacy store admin
        pharmacy_name: Name of the medical store / pharmacy
        primary_counter: Name of primary counter
        has_inventory: Boolean flag indicating if pharmacy has items

    Returns:
        The agent's text response

    Raises:
        RuntimeError: If agent is not available (caller should fallback)
    """
    global _agent, _agent_available

    if not is_agent_available():
        raise RuntimeError("LLM agent not available")

    # Build the system prompt with current time + past context + admin profile
    system_prompt = get_system_prompt(
        current_date=datetime.now(),
        past_context=vector_context if vector_context else None,
        admin_name=admin_name,
        pharmacy_name=pharmacy_name,
        primary_counter=primary_counter,
        has_inventory=has_inventory,
    )

    # Build message list: system → history → current question
    messages = [{"role": "system", "content": system_prompt}]

    if conversation_history:
        # Include last 4 messages to keep token usage well within Groq TPM limits
        for msg in conversation_history[-4:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if content and role in {"user", "assistant"}:
                messages.append({"role": role, "content": str(content)[:1000]})

    messages.append({"role": "user", "content": question})

    def _invoke_with_retry():
        import time
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                return _agent.invoke({"messages": messages})
            except Exception as exc:
                err_str = str(exc).lower()
                is_rate_limit = "429" in err_str or "rate_limit" in err_str or "tpm" in err_str or "too many requests" in err_str
                if is_rate_limit and attempt < max_retries:
                    wait_s = 2 ** (attempt - 1)  # 1s, 2s, 4s backoff
                    logger.warning(
                        "Groq rate limit (429) on attempt %d/%d — retrying in %ds...",
                        attempt,
                        max_retries,
                        wait_s,
                    )
                    time.sleep(wait_s)
                else:
                    raise exc

    try:
        ctx = contextvars.copy_context()
        future = _agent_executor.submit(ctx.run, _invoke_with_retry)
        try:
            result = future.result(timeout=20)
        except concurrent.futures.TimeoutError:
            logger.error("Agent invocation timed out after 20s")
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
                return str(content)

        # Fallback: return the last message content if it has any.
        if agent_messages:
            last_content = getattr(agent_messages[-1], "content", None)
            return str(last_content) or "I couldn't generate a response. Please try rephrasing."

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

