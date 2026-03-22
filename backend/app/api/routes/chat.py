"""
Chat API routes.

Provides AI-powered chat for inventory queries with:
- LangGraph ReAct agent (Groq LLM) as primary path
- Rule-based fallback when LLM unavailable
- Vector memory RAG (ChromaDB) for cross-session context
- Conversation history within sessions
- Chat session ownership enforcement
"""

from fastapi import APIRouter, Depends
from app.core.exceptions import (
    ValidationError,
    AppException,
    NotFoundError,
    DatabaseError,
    AuthorizationError,
)
from app.core.dependencies import get_current_user
from app.infrastructure.database.models import User
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional
from app.infrastructure.database.connection import get_db
from app.infrastructure.database.models import ChatSession, ChatMessage
from app.application.agent_tools import (
    get_inventory_overview,
    get_critical_items,
    get_stock_health,
    calculate_reorder_suggestions,
    get_location_summary,
    get_category_analysis,
    get_consumption_trends,
    set_db_session,
)
from app.infrastructure.vector_store.vector_store import get_vector_memory
from app.application.agent_service import is_agent_available, invoke_agent
from app.core.config import settings
from app.api.schemas.chat_schemas import ChatRequest, ChatResponse
import httpx
import uuid
import logging
from datetime import datetime

logger = logging.getLogger("smart_inventory.chat")

router = APIRouter(prefix="/chat", tags=["Chatbot"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_conversation_history(db: Session, conversation_id: str, limit: int = 10) -> list[dict]:
    """Load the last N messages from a conversation for context."""
    session = db.query(ChatSession).filter(ChatSession.id == conversation_id).first()
    if not session or not session.messages:
        return []

    recent = session.messages[-limit:]
    return [{"role": msg.role, "content": msg.content} for msg in recent]


def _get_vector_context(question: str, conversation_id: str = "") -> str:
    """Retrieve relevant past context from vector memory."""
    try:
        memory = get_vector_memory()
        if not memory.is_available:
            return ""

        matches = memory.search_relevant(
            query=question,
            n_results=3,
            exclude_session=conversation_id or None,
        )

        if not matches:
            return ""

        context_parts = []
        for m in matches:
            context_parts.append(
                f"[{m['timestamp']}] ({m['role']}): {m['content'][:300]}"
            )

        return "\n".join(context_parts)
    except Exception as e:
        logger.warning("Vector memory retrieval failed: %s", e)
        return ""


def _build_agent_response(
    question: str, db: Session, conversation_id: Optional[str] = None
) -> dict:
    """Try LLM agent first, fall back to rule-based if unavailable."""
    set_db_session(db)

    # Check if inventory has data
    overview = get_inventory_overview.invoke({})
    if isinstance(overview, dict) and not overview.get("has_data"):
        return {
            "success": True,
            "response": (
                "Inventory data is empty. Add locations, items, and transactions from "
                "the Data Entry page first."
            ),
            "question": question,
        }

    # Gather context
    past_context = _get_vector_context(question, conversation_id or "")
    history = []
    if conversation_id:
        history = _get_conversation_history(db, conversation_id, limit=6)

    # ── Try LLM agent first ────────────────────────────────────────────
    if is_agent_available():
        try:
            response_text = invoke_agent(
                question=question,
                conversation_history=history,
                vector_context=past_context,
            )
            return {
                "success": True,
                "response": response_text,
                "question": question,
            }
        except RuntimeError as e:
            logger.warning("LLM agent failed, falling back to rule-based: %s", e)

    # ── Rule-based fallback ────────────────────────────────────────────
    return _rule_based_response(question, past_context)


def _rule_based_response(question: str, past_context: str = "") -> dict:
    """Keyword-matching fallback when LLM is unavailable."""
    question_lower = question.lower()

    if any(k in question_lower for k in ["trend", "usage", "consumption"]):
        result = get_consumption_trends.invoke({})
        return _format_result("Consumption trend summary", result, question, past_context)

    if any(k in question_lower for k in ["reorder", "order", "purchase"]):
        result = calculate_reorder_suggestions.invoke({})
        return _format_result("Reorder suggestions", result, question, past_context)

    if any(k in question_lower for k in ["critical", "warning", "alert"]):
        severity = "WARNING" if "warning" in question_lower else "CRITICAL"
        result = get_critical_items.invoke({"severity": severity})
        return _format_result(f"{severity} stock alerts", result, question, past_context)

    if "category" in question_lower:
        result = get_category_analysis.invoke({"category": ""})
        return _format_result("Category snapshot", result, question, past_context)

    result = get_stock_health.invoke({})
    return _format_result("Current stock health", result, question, past_context)


def _format_result(title: str, payload, question: str, past_context: str = "") -> dict:
    import json

    prefix = ""
    if past_context:
        prefix = f"(Based on past context)\n"

    if isinstance(payload, dict):
        if payload.get("error"):
            return {
                "success": True,
                "response": f"{title}: {payload['error']}",
                "question": question,
            }
        if payload.get("info"):
            return {"success": True, "response": f"{prefix}{payload['info']}", "question": question}
        return {
            "success": True,
            "response": f"{prefix}{title}:\n{json.dumps(payload, indent=2)}",
            "question": question,
        }

    if isinstance(payload, list):
        if not payload:
            return {
                "success": True,
                "response": f"{title}: no data found.",
                "question": question,
            }
        first = payload[0]
        if isinstance(first, dict) and first.get("info"):
            return {"success": True, "response": f"{prefix}{first['info']}", "question": question}
        if isinstance(first, dict) and first.get("error"):
            return {
                "success": True,
                "response": f"{title}: {first['error']}",
                "question": question,
            }
        return {
            "success": True,
            "response": f"{prefix}{title}:\n{json.dumps(payload[:10], indent=2)}",
            "question": question,
        }

    return {
        "success": True,
        "response": f"{prefix}{title}: {str(payload)}",
        "question": question,
    }


def _verify_session_ownership(db: Session, conversation_id: str, user_id: int) -> None:
    """Ensure the conversation belongs to the requesting user."""
    session = db.query(ChatSession).filter(ChatSession.id == conversation_id).first()
    if session and session.user_id != str(user_id):
        raise AuthorizationError("You do not have access to this conversation")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/query", response_model=ChatResponse)
def chat_query(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not request.question or len(request.question.strip()) < 3:
        raise ValidationError("Question must be at least 3 characters")

    # Verify ownership if continuing an existing conversation
    if request.conversation_id:
        _verify_session_ownership(db, request.conversation_id, current_user.id)

    try:
        result = _build_agent_response(
            request.question, db, request.conversation_id or ""
        )

        conv_id = request.conversation_id
        if not conv_id:
            conv_id = f"conv_{uuid.uuid4().hex[:12]}"
            title = (
                request.question[:50] + "..."
                if len(request.question) > 50
                else request.question
            )
            session = ChatSession(id=conv_id, user_id=str(current_user.id), title=title)
            db.add(session)

        db.add(ChatMessage(session_id=conv_id, role="user", content=request.question))
        db.add(
            ChatMessage(
                session_id=conv_id, role="assistant", content=result["response"]
            )
        )
        db.commit()

        # Store in vector memory for future RAG
        try:
            memory = get_vector_memory()
            if memory.is_available:
                now = datetime.now()
                memory.add_message(conv_id, "user", request.question, now)
                memory.add_message(conv_id, "assistant", result["response"], now)
        except Exception as e:
            logger.warning("Failed to store in vector memory: %s", e)

        response_lower = result["response"].lower()
        suggested_actions = []
        if any(word in response_lower for word in ["order", "purchase", "reorder"]):
            suggested_actions.append(
                {
                    "type": "export",
                    "label": "Download Purchase Order",
                    "action": "export_reorder_list",
                }
            )
        if "critical" in response_lower or "urgent" in response_lower:
            suggested_actions.append(
                {"type": "view", "label": "View All Alerts", "action": "view_alerts"}
            )

        return ChatResponse(
            success=True,
            response=result["response"],
            question=request.question,
            conversation_id=conv_id,
            suggested_actions=suggested_actions if suggested_actions else None,
        )

    except (ValidationError, AppException, AuthorizationError):
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error("Database error in chat_query: %s", str(e))
        raise DatabaseError(f"Failed to save chat message: {str(e)}")
    except Exception as e:
        db.rollback()
        logger.error("Unexpected error in chat_query: %s", str(e))
        raise AppException(f"An unexpected error occurred: {str(e)}")


@router.get("/history/{conversation_id}")
def get_chat_history(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(ChatSession).filter(ChatSession.id == conversation_id).first()
    if not session:
        raise NotFoundError("Conversation", conversation_id)

    # Ownership check
    _verify_session_ownership(db, conversation_id, current_user.id)

    messages = [{"role": msg.role, "content": msg.content} for msg in session.messages]

    return {"success": True, "conversation_id": conversation_id, "messages": messages}


@router.delete("/history/{conversation_id}")
def clear_chat_history(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(ChatSession).filter(ChatSession.id == conversation_id).first()
    if not session:
        raise NotFoundError("Conversation", conversation_id)

    # Ownership check
    _verify_session_ownership(db, conversation_id, current_user.id)

    db.delete(session)
    db.commit()
    return {"success": True, "message": "Conversation history cleared"}


@router.get("/suggestions")
def get_question_suggestions(
    current_user: User = Depends(get_current_user),
):
    return {
        "success": True,
        "suggestions": [
            {
                "category": "Alerts",
                "questions": [
                    "What items are critical right now?",
                    "Show me all warning-level items",
                    "Which locations have the most issues?",
                ],
            },
            {
                "category": "Location-Specific",
                "questions": [
                    "What's the stock status for my main warehouse?",
                    "Show me critical items for location 1",
                    "How is Central Clinic doing?",
                ],
            },
            {
                "category": "Item-Specific",
                "questions": [
                    "Do we have enough paracetamol?",
                    "Show me all antibiotic levels",
                    "What's our inventory for item 3?",
                ],
            },
            {
                "category": "Reorder",
                "questions": [
                    "What should I order today?",
                    "Generate purchase order for my location",
                    "Show me reorder recommendations",
                ],
            },
            {
                "category": "Analysis",
                "questions": [
                    "Which category has most shortages?",
                    "Compare stock levels across locations",
                    "Show me consumption trends",
                ],
            },
        ],
    }


@router.get("/sessions")
def get_chat_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Filter sessions by the current user only
    db_sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == str(current_user.id))
        .order_by(ChatSession.updated_at.desc())
        .all()
    )

    sessions = []
    for s in db_sessions:
        message_count = len(s.messages)
        if message_count > 0:
            sessions.append(
                {"id": s.id, "preview": s.title, "message_count": message_count}
            )

    return {"success": True, "sessions": sessions}

