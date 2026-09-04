"""
Chat API routes.

Provides AI-powered chat for inventory queries with:
- LangGraph ReAct agent (Groq LLM) as primary path
- Rule-based fallback when LLM unavailable
- Vector memory RAG (ChromaDB) for cross-session context
- Conversation history within sessions
- Chat session ownership enforcement
"""

import time
from fastapi import APIRouter, Depends, Request, UploadFile, File
from app.core.rate_limiter import limiter
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


def _get_vector_context(
    question: str,
    conversation_id: str = "",
    org_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> tuple[str, float]:
    """Retrieve relevant past context from vector memory with execution duration in ms."""
    t0 = time.perf_counter()
    try:
        memory = get_vector_memory()
        if not memory.is_available:
            return "", (time.perf_counter() - t0) * 1000

        matches = memory.search_relevant(
            query=question,
            n_results=3,
            exclude_session=conversation_id or None,
            org_id=org_id,
            user_id=user_id,
        )

        if not matches:
            return "", (time.perf_counter() - t0) * 1000

        context_parts = []
        for m in matches:
            context_parts.append(
                f"[{m['timestamp']}] ({m['role']}): {m['content'][:300]}"
            )

        return "\n".join(context_parts), (time.perf_counter() - t0) * 1000
    except Exception as e:
        logger.warning("Vector memory retrieval failed: %s", e)
        return "", (time.perf_counter() - t0) * 1000


def _is_greeting(text: str) -> bool:
    """Return True if the message is conversational rather than an inventory question."""
    text_lower = text.lower().strip()
    greeting_keywords = [
        "hi", "hello", "hey", "hii", "helo",
        "good morning", "good afternoon", "good evening",
        "how are you", "who are you", "what can you do",
        "my name is", "i am ", "i'm ", "thanks", "thank you",
        "bye", "goodbye", "ok", "okay", "cool", "great",
    ]
    return any(text_lower.startswith(kw) or kw in text_lower for kw in greeting_keywords)


def _build_agent_response(
    question: str,
    db: Session,
    conversation_id: Optional[str] = None,
    org_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> dict:
    """Try LLM agent first, fall back to rule-based if unavailable."""
    rag_start = time.perf_counter()
    set_db_session(db, org_id=org_id)

    from app.infrastructure.database.models import User as UserModel, Organization as OrgModel, Item as ItemModel

    # Fetch admin and organization context
    admin_user = db.query(UserModel).filter(UserModel.id == user_id).first() if user_id else None
    org = db.query(OrgModel).filter(OrgModel.id == org_id).first() if org_id else None

    admin_name = (admin_user.full_name or admin_user.username) if admin_user else "Store Admin"
    pharmacy_name = org.name if org else "Pharmacy & Medical Store"
    primary_counter = (org.settings or {}).get("primary_counter_name", "Main Market Counter") if org else "Main Counter"

    # Check if this pharmacy currently has any items/inventory in DB
    has_inventory = (
        db.query(ItemModel).filter(ItemModel.org_id == org_id).count() > 0
        if org_id
        else True
    )

    # Stage 1: Vector Retrieval Timing
    past_context, vector_retrieval_ms = _get_vector_context(
        question, conversation_id or "", org_id=org_id, user_id=user_id
    )
    history = []
    if conversation_id:
        history = _get_conversation_history(db, conversation_id, limit=6)

    # ── Try LLM agent first ────────────────────────────────────────────
    llm_inference_ms = 0.0
    if is_agent_available():
        try:
            llm_t0 = time.perf_counter()
            response_text = invoke_agent(
                question=question,
                conversation_history=history,
                vector_context=past_context,
                admin_name=admin_name,
                pharmacy_name=pharmacy_name,
                primary_counter=primary_counter,
                has_inventory=has_inventory,
            )
            llm_inference_ms = (time.perf_counter() - llm_t0) * 1000
            total_rag_ms = (time.perf_counter() - rag_start) * 1000

            logger.info(
                "🤖 AI RAG Latency Breakdown | Vector Retrieval: %.2fms | LLM Inference: %.2fms | Total RAG: %.2fms",
                vector_retrieval_ms,
                llm_inference_ms,
                total_rag_ms,
            )

            return {
                "success": True,
                "response": response_text,
                "question": question,
                "timings": {
                    "vector_retrieval_ms": round(vector_retrieval_ms, 2),
                    "llm_inference_ms": round(llm_inference_ms, 2),
                    "total_rag_ms": round(total_rag_ms, 2),
                },
            }
        except RuntimeError as e:
            logger.warning("LLM agent failed, falling back to rule-based: %s", e)

    # ── Rule-based fallback ────────────────────────────────────────────
    total_rag_ms = (time.perf_counter() - rag_start) * 1000
    res = _rule_based_response(
        question=question,
        past_context=past_context,
        admin_name=admin_name,
        pharmacy_name=pharmacy_name,
        has_inventory=has_inventory,
    )
    res["timings"] = {
        "vector_retrieval_ms": round(vector_retrieval_ms, 2),
        "llm_inference_ms": 0.0,
        "total_rag_ms": round(total_rag_ms, 2),
    }
    return res


def _rule_based_response(
    question: str,
    past_context: str = "",
    admin_name: str = "Store Admin",
    pharmacy_name: str = "your pharmacy store",
    has_inventory: bool = True,
) -> dict:
    """Intelligent fallback when LLM is unavailable or for conversational greetings."""
    question_lower = question.lower().strip()

    # 1. Conversational greetings & identity questions
    if _is_greeting(question) or any(w in question_lower for w in ["who are you", "what can you do", "assistant"]):
        if not has_inventory:
            msg = (
                f"Hello {admin_name}! Welcome to InvIQ for {pharmacy_name}.\n\n"
                f"I am your dedicated personal inventory intelligence copilot. "
                f"You are currently all set up with your store workspace. Since you haven't added any medicine stock or uploaded invoices yet, "
                f"your stock dashboard is currently at zero.\n\n"
                f"To get started, you can:\n"
                f"• Add medicines and batches in the Inventory section\n"
                f"• Upload supplier invoices in Suppliers & Vendors\n"
                f"• Configure your retail counter locations in Store & Branches\n\n"
                f"How can I help you set up your pharmacy today?"
            )
        else:
            msg = (
                f"Hello {admin_name}! I am your personal inventory assistant for {pharmacy_name}. "
                f"I'm monitoring your stock levels, near-expiry alerts, and reorder thresholds in real time. "
                f"What would you like to check today?"
            )
        return {"success": True, "response": msg, "question": question}

    # 2. If empty inventory, respond cleanly without confusing errors
    if not has_inventory:
        return {
            "success": True,
            "response": (
                f"No medicine stock records found for {pharmacy_name} yet. "
                f"Once you add inventory items or import supplier invoices, I will track stock health, "
                f"critical shortages, and reorder suggestions here in real time."
            ),
            "question": question,
        }

    # 3. Keyword matching for existing inventory
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
    from decimal import Decimal
    from datetime import date, datetime

    def _json_safe(obj):
        """Custom JSON serializer for types json.dumps() can't handle by default."""
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    prefix = ""
    if past_context:
        prefix = "(Based on past context)\n"

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
            "response": f"{prefix}{title}:\n{json.dumps(payload, indent=2, default=_json_safe)}",
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
            "response": f"{prefix}{title}:\n{json.dumps(payload[:10], indent=2, default=_json_safe)}",
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
    if session and session.user_id != user_id:
        raise AuthorizationError("You do not have access to this conversation")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/query", response_model=ChatResponse)
@limiter.limit("20/minute")
def chat_query(
    request: Request,
    chat_request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not chat_request.question or len(chat_request.question.strip()) < 3:
        raise ValidationError("Question must be at least 3 characters")

    if current_user.role != "admin":
        raise AuthorizationError("The AI Assistant is reserved for Pharmacy Administrators and Store Owners.")

    # All users must be assigned to an organization
    if current_user.org_id is None:
        raise AuthorizationError("User is not assigned to an organization")

    # Verify ownership if continuing an existing conversation
    if chat_request.conversation_id:
        _verify_session_ownership(db, chat_request.conversation_id, current_user.id)

    try:
        caller_org_id = current_user.org_id
        result = _build_agent_response(
            chat_request.question,
            db,
            chat_request.conversation_id or "",
            org_id=caller_org_id,
            user_id=current_user.id,
        )


        conv_id = chat_request.conversation_id
        if not conv_id:
            conv_id = f"conv_{uuid.uuid4().hex[:12]}"
            title = (
                chat_request.question[:50] + "..."
                if len(chat_request.question) > 50
                else chat_request.question
            )
            session = ChatSession(id=conv_id, user_id=current_user.id, title=title)
            db.add(session)

        db.add(ChatMessage(session_id=conv_id, role="user", content=chat_request.question))
        db.add(
            ChatMessage(
                session_id=conv_id, role="assistant", content=result["response"]
            )
        )
        db.commit()

        # Store in vector memory for future RAG (tenant-scoped)
        try:
            memory = get_vector_memory()
            if memory.is_available:
                now = datetime.now()
                memory.add_message(
                    conv_id, "user", chat_request.question, now,
                    org_id=current_user.org_id, user_id=current_user.id,
                )
                memory.add_message(
                    conv_id, "assistant", result["response"], now,
                    org_id=current_user.org_id, user_id=current_user.id,
                )
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
            question=chat_request.question,
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
@limiter.limit("10/minute")
def clear_chat_history(
    conversation_id: str,
    request: Request,
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
        .filter(ChatSession.user_id == current_user.id)
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


# ── Audio Upload Security Policy ──────────────────────────────────────────
MAX_AUDIO_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB strict limit for speech audio
ALLOWED_AUDIO_MIME_TYPES = {
    "audio/webm",
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
    "audio/mp3",
    "audio/mpeg",
    "audio/m4a",
    "audio/mp4",
    "audio/ogg",
    "audio/flac",
    "audio/aac",
    "audio/x-m4a",
    "application/octet-stream",
}


@router.post("/transcribe")
@limiter.limit("20/minute")
async def transcribe_audio(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Transcribe spoken English audio to text using Sarvam AI Saaras v3 STT.

    Security & Performance Guarantees:
    - Strict 10MB file size boundary enforced via streaming chunked read (prevents RAM exhaustion).
    - MIME type & signature verification.
    - Spoken audio → Sarvam STT (language_code="en-IN", mode="transcribe") → English text.
    """
    if not settings.SARVAM_API_KEY:
        raise ValidationError("Sarvam AI API key is not configured on the server")

    content_type = (file.content_type or "").lower().split(";")[0].strip()
    if content_type and content_type not in ALLOWED_AUDIO_MIME_TYPES:
        raise ValidationError(f"Unsupported audio format: '{content_type}'. Supported: webm, wav, mp3, m4a, ogg, flac")

    # 1. Stream in chunks with cumulative size guard (prevents unbounded memory consumption)
    chunk_size = 64 * 1024  # 64 KB
    chunks = []
    total_bytes = 0

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_bytes += len(chunk)
        if total_bytes > MAX_AUDIO_SIZE_BYTES:
            raise ValidationError(
                f"Uploaded audio exceeds the maximum size limit of {MAX_AUDIO_SIZE_BYTES // (1024 * 1024)}MB"
            )
        chunks.append(chunk)

    if total_bytes < 32:
        raise ValidationError("Audio file is empty or too short to process")

    content = b"".join(chunks)

    # 2. Audio signature verification (magic header check)
    is_valid_audio = (
        content.startswith(b"\x1a\x45\xdf\xa3")  # WebM / Matroska
        or content.startswith(b"RIFF")          # WAV
        or content.startswith(b"ID3")           # MP3 ID3v2
        or content.startswith(b"\xff\xfb")      # MP3 frame
        or content.startswith(b"\xff\xf3")      # MP3 frame
        or content.startswith(b"OggS")          # OGG
        or content.startswith(b"fLaC")          # FLAC
        or b"ftyp" in content[:32]              # M4A / MP4 audio container
    )
    if not is_valid_audio and content_type not in ["audio/webm", "audio/wav"]:
        raise ValidationError("Invalid audio file signature: file does not contain valid audio data")

    try:
        from sarvamai import SarvamAI

        client = SarvamAI(api_subscription_key=settings.SARVAM_API_KEY)

        codec = "webm"
        if content.startswith(b"RIFF") or "wav" in content_type:
            codec = "wav"
        elif content.startswith(b"ID3") or "mp3" in content_type or "mpeg" in content_type:
            codec = "mp3"

        response = client.speech_to_text.transcribe(
            file=(file.filename or f"audio.{codec}", content, file.content_type or f"audio/{codec}"),
            model="saaras:v3",
            mode="transcribe",
            language_code="en-IN",
            input_audio_codec=codec,
        )

        transcribed_text = (response.transcript or "").strip()

        logger.info(
            "Sarvam English STT complete for user=%s size=%d bytes length=%d chars",
            current_user.username,
            total_bytes,
            len(transcribed_text),
        )

        return {
            "success": True,
            "text": transcribed_text,
        }

    except Exception as e:
        logger.error("Sarvam STT error user=%s: %s", current_user.username, str(e))
        raise ValidationError(f"Transcription failed: {str(e)}")



