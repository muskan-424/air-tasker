import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import SessionLocal, get_db
from app.models.chat import ChatMessage, ChatSession
from app.models.user import User
from app.schemas.chat import (
    AgentChatRequest,
    AgentChatResponse,
    AgentClassifyRequest,
    ChatHistoryMessage,
    ChatHistoryResponse,
    ChatRefineRequest,
    ChatRefineResponse,
    ChatTranslateRequest,
    ChatTranslateResponse,
)
from app.services.agent_chat_service import agent_chat_service
from app.services.gemini_structured_service import classify_message
from app.services.translation_service import stub_translate, translate_sync

router = APIRouter(prefix="/api/chat", tags=["chat"])


async def _get_or_create_session(db: AsyncSession, user: User, session_id: str | None) -> ChatSession:
    if session_id:
        try:
            sid = uuid.UUID(session_id)
            existing = (
                await db.execute(select(ChatSession).where(ChatSession.id == sid, ChatSession.user_id == user.id))
            ).scalar_one_or_none()
            if existing:
                return existing
        except ValueError:
            pass
    session = ChatSession(user_id=user.id, title="Agent Chat")
    db.add(session)
    await db.flush()
    return session


@router.post("/classify", response_model=dict)
async def classify_intent(
    payload: AgentClassifyRequest,
    current_user: User = Depends(get_current_user),
):
    _ = current_user.id
    return classify_message(payload.message)


@router.post("/translate", response_model=ChatTranslateResponse)
async def translate_chat(
    payload: ChatTranslateRequest,
    current_user: User = Depends(get_current_user),
):
    _ = current_user.id
    if settings.gemini_api_key and not settings.use_mock_chatbot:
        try:
            translated, src_out, detected, provider = await asyncio.to_thread(
                translate_sync, payload.text, payload.source_lang, payload.target_lang, settings
            )
            return ChatTranslateResponse(
                original_text=payload.text,
                translated_text=translated,
                source_lang=src_out,
                target_lang=payload.target_lang,
                provider=provider,
                note=None,
                detected_source_lang=detected,
            )
        except Exception:
            pass
    translated, src_out, detected, provider = stub_translate(
        payload.text, payload.target_lang, payload.source_lang
    )
    return ChatTranslateResponse(
        original_text=payload.text,
        translated_text=translated,
        source_lang=src_out,
        target_lang=payload.target_lang,
        provider=provider,
        note="Set GEMINI_API_KEY and USE_MOCK_CHATBOT=false for Gemini translation.",
        detected_source_lang=detected,
    )


@router.post("/agent", response_model=AgentChatResponse)
async def agent_chat(
    payload: AgentChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await _get_or_create_session(db, current_user, payload.session_id)
    db.add(ChatMessage(session_id=session.id, role="user", text=payload.message))

    response = await agent_chat_service.respond(
        db=db,
        user=current_user,
        message=payload.message,
        language=payload.language,
        tone=payload.tone,
    )

    db.add(ChatMessage(session_id=session.id, role="assistant", text=response.reply, intent=response.intent))
    await db.commit()

    response.session_id = str(session.id)
    return response


@router.post("/refine", response_model=ChatRefineResponse)
async def refine_chat_response(
    payload: ChatRefineRequest,
    current_user: User = Depends(get_current_user),
):
    _ = current_user.id
    refined = agent_chat_service.refine_answer(payload.original_answer, payload.instruction, payload.language)
    return ChatRefineResponse(refined_answer=refined)


@router.get("/history/{session_id}", response_model=ChatHistoryResponse)
async def chat_history(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        return ChatHistoryResponse(session_id=session_id, messages=[])

    session = (await db.execute(select(ChatSession).where(ChatSession.id == sid))).scalar_one_or_none()
    if not session or session.user_id != current_user.id:
        return ChatHistoryResponse(session_id=session_id, messages=[])

    messages = (
        await db.execute(select(ChatMessage).where(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at))
    ).scalars().all()
    return ChatHistoryResponse(
        session_id=str(session.id),
        messages=[ChatHistoryMessage(role=m.role, text=m.text, intent=m.intent) for m in messages],
    )


@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket):
    """
    Conversational agent over WebSocket. Auth: pass JWT as query param `token=...`.
    Client sends JSON: {"type":"message","text":"...","language":"en","tone":"friendly","session_id":null}
    Server replies: {"type":"reply", ...AgentChatResponse fields..., "session_id":"..."}
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="missing token")
        return
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_uuid = uuid.UUID(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        await websocket.close(code=1008, reason="invalid token")
        return

    async with SessionLocal() as db:
        user = (await db.execute(select(User).where(User.id == user_uuid))).scalar_one_or_none()
    if not user:
        await websocket.close(code=1008, reason="user not found")
        return

    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "detail": "invalid json"})
                continue
            msg_type = body.get("type", "message")
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            if msg_type != "message":
                await websocket.send_json({"type": "error", "detail": "use type message or ping"})
                continue
            text = (body.get("text") or "").strip()
            if not text:
                await websocket.send_json({"type": "error", "detail": "empty text"})
                continue
            lang = body.get("language") or "en"
            tone = body.get("tone") or "friendly"
            sid = body.get("session_id")

            async with SessionLocal() as db:
                session = await _get_or_create_session(db, user, sid)
                db.add(ChatMessage(session_id=session.id, role="user", text=text))
                response = await agent_chat_service.respond(
                    db=db, user=user, message=text, language=lang, tone=tone
                )
                db.add(ChatMessage(session_id=session.id, role="assistant", text=response.reply, intent=response.intent))
                await db.commit()
                response.session_id = str(session.id)

            await websocket.send_json({"type": "reply", **response.model_dump()})
    except WebSocketDisconnect:
        return

