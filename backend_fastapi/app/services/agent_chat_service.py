from __future__ import annotations

import asyncio
import re
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.task import Task, TaskAcceptance, TaskStatus
from app.models.task_draft import TaskDraft
from app.models.user import User, UserRole
from app.schemas.chat import AgentChatResponse, AgentToolTrace
from app.services.agent_confidence import confidence_for_response, confidence_from_tool_trace
from app.services.gemini_chat_service import refine_with_gemini, synthesize_reply
from app.services.hybrid_rag_service import HybridRAGService
from app.services.task_chat_schema_service import build_ai_schema_from_message
from app.services.task_publish_service import PublishDraftError, publish_draft_to_task


_LOW_CONF_NOTE = (
    "\n\n— Note: confidence is low for this reply; please verify important details in the app."
)


class AgentChatService:
    def __init__(self) -> None:
        project_root = Path(__file__).resolve().parents[3]
        self.rag = HybridRAGService(project_root=project_root)

    @staticmethod
    def _append_low_conf_if_needed(text: str, confidence: float) -> str:
        if confidence >= settings.agent_confidence_threshold:
            return text
        if not settings.low_confidence_append_note:
            return text
        if "confidence is low" in text.lower():
            return text
        return text + _LOW_CONF_NOTE

    async def _finalize_llm_reply(
        self,
        draft: str,
        intent: str,
        message: str,
        language: str,
        confidence: float,
        tone: str,
    ) -> tuple[str, str | None]:
        if settings.skip_gemini_on_low_confidence and confidence < settings.agent_confidence_threshold:
            return self._append_low_conf_if_needed(draft, confidence), "rule"
        if not settings.gemini_api_key or settings.use_mock_chatbot:
            return self._append_low_conf_if_needed(draft, confidence), "rule"
        out = await asyncio.to_thread(
            synthesize_reply,
            intent=intent,
            user_message=message,
            facts_block=draft,
            language=language,
            tone=tone or settings.default_chat_tone,
            app_settings=settings,
        )
        if out:
            return self._append_low_conf_if_needed(out, confidence), "gemini"
        return self._append_low_conf_if_needed(draft, confidence), "rule"

    @staticmethod
    def _flags(confidence: float) -> dict:
        thr = settings.agent_confidence_threshold
        return {
            "confidence": round(float(confidence), 4),
            "needs_verification": confidence < thr,
        }

    @staticmethod
    def _detect_intent(message: str) -> str:
        m = message.lower()
        if "last" in m and ("order" in m or "task" in m) or "mera 5 order" in m:
            return "order_lookup"
        if "near" in m or "nearby" in m or "earning" in m or "jobs" in m:
            return "task_discovery"
        starters = (
            "create task",
            "post task",
            "job create",
            "task banana",
            "task banao",
            "post a task",
            "new task",
            "task create",
            "task post",
            "task likho",
        )
        for s in starters:
            if m.startswith(s) or m.startswith(s + "?") or m.startswith(s + "!"):
                return "task_creation_assistant"
        if "create task" in m or "post task" in m or "job create" in m or "task banao" in m:
            return "task_creation_assistant"
        if "what this app" in m or "app does" in m or "ye app" in m:
            return "app_help"
        return "general_help"

    @staticmethod
    def _detect_publish_intent(message: str) -> bool:
        m = message.lower()
        if "don't publish" in m or "do not publish" in m or "mat publish" in m:
            return False
        keys = (
            "publish",
            "go live",
            "live karo",
            "post kar do",
            "confirm publish",
            "draft publish",
            "publish karo",
            "publish kar do",
        )
        return any(k in m for k in keys)

    @staticmethod
    def _is_insufficient_task_description(message: str) -> bool:
        t = message.strip()
        if len(t) < 22:
            return True
        low = t.lower().strip("?.!")
        brief = (
            "create task",
            "post task",
            "job create",
            "task banana",
            "task banao",
            "post a task",
            "new task",
            "task create",
            "task post",
            "task likho",
        )
        if low in brief:
            return True
        for b in brief:
            if low.startswith(b + " ") and len(t) < 55:
                return True
        return False

    async def _resolve_draft_id_for_publish(
        self, db: AsyncSession, user: User, message: str
    ) -> uuid.UUID | None:
        ids = re.findall(r"[0-9a-fA-F-]{36}", message)
        for raw in ids:
            try:
                candidate = uuid.UUID(raw)
            except ValueError:
                continue
            d = (
                await db.execute(
                    select(TaskDraft).where(TaskDraft.id == candidate, TaskDraft.poster_id == user.id)
                )
            ).scalar_one_or_none()
            if not d:
                continue
            if (await db.execute(select(Task).where(Task.draft_id == d.id))).scalar_one_or_none():
                continue
            return candidate

        q = select(TaskDraft).where(TaskDraft.poster_id == user.id).order_by(TaskDraft.created_at.desc())
        drafts = (await db.execute(q)).scalars().all()
        for d in drafts:
            if not (await db.execute(select(Task).where(Task.draft_id == d.id))).scalar_one_or_none():
                return d.id
        return None

    async def _tool_create_task_draft_from_chat(
        self, db: AsyncSession, user: User, message: str
    ) -> tuple[str, AgentToolTrace]:
        ai = build_ai_schema_from_message(message)
        draft = TaskDraft(
            poster_id=user.id,
            ai_schema=ai,
            ai_explain="Created from chat (rule-based schema).",
        )
        db.add(draft)
        await db.commit()
        await db.refresh(draft)
        pr = ai.get("suggestedPriceRange") or {}
        text = (
            f"Draft save ho gaya.\n"
            f"draft_id: {draft.id}\n"
            f"Category: {ai.get('category')} | Budget hint: INR {pr.get('min')}-{pr.get('max')}\n\n"
            f"Live karne ke liye chat me bolo: publish (ya REST: POST /api/tasks/{draft.id}/publish)."
        )
        return text, AgentToolTrace(name="create_task_draft", used=True, details=f"draft_id={draft.id}")

    async def _tool_publish_draft_from_chat(
        self, db: AsyncSession, user: User, message: str
    ) -> tuple[str, AgentToolTrace]:
        did = await self._resolve_draft_id_for_publish(db, user, message)
        if not did:
            return (
                "Koi unpublished draft nahi mila. Pehle task ka description bhejo, jaise: "
                "'create task: plumber needed for leaking tap in Indirapuram, budget 800'.",
                AgentToolTrace(name="publish_draft", used=True, details="no_draft"),
            )
        try:
            task = await publish_draft_to_task(db, user, did)
        except PublishDraftError as e:
            return (
                f"Publish nahi ho saka: {e!s}",
                AgentToolTrace(name="publish_draft", used=True, details=f"error={e.code}"),
            )
        return (
            f"Task live ho gaya. task_id: {task.id}\nTaskers ab apply kar sakte hain.",
            AgentToolTrace(name="publish_draft", used=True, details=f"task_id={task.id}"),
        )

    @staticmethod
    def _extract_limit(message: str, default: int = 5) -> int:
        numbers = re.findall(r"\d+", message)
        if not numbers:
            return default
        value = int(numbers[0])
        return min(max(value, 1), 20)

    async def _tool_last_orders(self, db: AsyncSession, user: User, limit: int) -> tuple[str, AgentToolTrace]:
        if user.role == UserRole.TASKER:
            q = (
                select(Task)
                .join(TaskAcceptance, TaskAcceptance.task_id == Task.id)
                .where(TaskAcceptance.tasker_id == user.id)
                .order_by(Task.created_at.desc())
                .limit(limit)
            )
        else:
            q = select(Task).where(Task.poster_id == user.id).order_by(Task.created_at.desc()).limit(limit)

        rows = (await db.execute(q)).scalars().all()
        if not rows:
            return (
                "Mujhe aapke account me recent orders/tasks nahi mile. Aap chatbot se direct naya task create kar sakte ho.",
                AgentToolTrace(name="get_user_orders", used=True, details="no_records"),
            )

        lines = []
        for idx, t in enumerate(rows, start=1):
            lines.append(f"{idx}. {t.category} | status: {t.status.value} | task_id: {t.id}")
        msg = "Ye rahe aapke recent tasks/orders:\n" + "\n".join(lines)
        return msg, AgentToolTrace(name="get_user_orders", used=True, details=f"count={len(rows)}")

    async def _tool_discovery(self, db: AsyncSession, message: str) -> tuple[str, AgentToolTrace]:
        m = message.lower()
        query = select(Task).where(Task.status == TaskStatus.PUBLISHED)
        if "tech" in m:
            query = query.where(Task.category.in_(["tech", "it", "computers", "web", "general"]))
        query = query.order_by(Task.created_at.desc()).limit(5)
        tasks = (await db.execute(query)).scalars().all()
        if not tasks:
            return (
                "Abhi nearby matching tasks kam hain. Main aapke liye alert set kar sakta hoon jab high-earning tasks aaye.",
                AgentToolTrace(name="search_tasks", used=True, details="no_matches"),
            )
        lines = []
        for idx, t in enumerate(tasks, start=1):
            range_data = t.task_schema.get("suggestedPriceRange", {}) if isinstance(t.task_schema, dict) else {}
            min_p = range_data.get("min", "NA")
            max_p = range_data.get("max", "NA")
            lines.append(f"{idx}. {t.category} | est earning INR {min_p}-{max_p} | task_id: {t.id}")
        return (
            "Aapke liye relevant tasks:\n"
            + "\n".join(lines)
            + "\nTip: previous similar tech tasks mostly INR 800-2500 range me milte hain.",
            AgentToolTrace(name="search_tasks", used=True, details=f"count={len(tasks)}"),
        )

    def _tool_rag_answer(self, message: str) -> tuple[str, AgentToolTrace, list[float] | None]:
        chunks, rag_source = self.rag.retrieve(message, top_k=3)
        if not chunks:
            return (
                "Yeh app AI-first marketplace hai jahan task post, task discovery, escrow, verification aur disputes handled hote hain. Agar chaho to main details step-by-step bata doon.",
                AgentToolTrace(name="rag_lookup", used=True, details="fallback_summary|rag=none"),
                None,
            )
        scores = [c.score for c in chunks]
        stitched = "\n".join([f"- ({c.source}, score={c.score:.3f}) {c.text[:220]}..." for c in chunks])
        return (
            f"Maine relevant context nikala hai:\n{stitched}\nAgar chaho to isko concise ya Hindi me refine kar deta hoon.",
            AgentToolTrace(name="rag_lookup", used=True, details=f"chunks={len(chunks)}|rag={rag_source}"),
            scores,
        )

    async def _tool_apply_to_task(
        self, db: AsyncSession, user: User, message: str
    ) -> tuple[str, AgentToolTrace]:
        if user.role != UserRole.TASKER:
            return (
                "Apply action ke liye TASKER role required hai.",
                AgentToolTrace(name="apply_to_task", used=True, details="role_not_tasker"),
            )
        task_ids = re.findall(r"[0-9a-fA-F-]{36}", message)
        if not task_ids:
            return (
                "Please task_id bhejo, fir main direct chatbot se apply karwa dunga.",
                AgentToolTrace(name="apply_to_task", used=True, details="missing_task_id"),
            )
        try:
            task_uuid = uuid.UUID(task_ids[0])
        except ValueError:
            return (
                "Task id format invalid hai, valid task_id share karo.",
                AgentToolTrace(name="apply_to_task", used=True, details="invalid_task_id"),
            )

        task = (await db.execute(select(Task).where(Task.id == task_uuid))).scalar_one_or_none()
        if not task:
            return (
                "Ye task_id mujhe nahi mila.",
                AgentToolTrace(name="apply_to_task", used=True, details="task_not_found"),
            )
        if task.status != TaskStatus.PUBLISHED:
            return (
                "Ye task currently apply ke liye available nahi hai.",
                AgentToolTrace(name="apply_to_task", used=True, details=f"status={task.status.value}"),
            )

        existing = (
            await db.execute(
                select(TaskAcceptance).where(TaskAcceptance.task_id == task.id, TaskAcceptance.tasker_id == user.id)
            )
        ).scalar_one_or_none()
        if existing:
            return (
                "Aap is task par already apply/accept kar chuke ho.",
                AgentToolTrace(name="apply_to_task", used=True, details="already_applied"),
            )

        acceptance = TaskAcceptance(
            task_id=task.id,
            tasker_id=user.id,
            acknowledgement={"source": "chatbot_apply"},
        )
        task.status = TaskStatus.ACCEPTED
        db.add(acceptance)
        await db.commit()
        return (
            f"Done. Aapka application accept ho gaya. task_id: {task.id}",
            AgentToolTrace(name="apply_to_task", used=True, details="applied"),
        )

    async def respond(
        self,
        db: AsyncSession,
        user: User,
        message: str,
        language: str = "en",
        tone: str = "friendly",
    ) -> AgentChatResponse:
        intent = self._detect_intent(message)
        traces: list[AgentToolTrace] = []

        if "apply" in message.lower() and "task" in message.lower():
            text, trace = await self._tool_apply_to_task(db, user, message)
            traces.append(trace)
            conf = confidence_from_tool_trace(trace)
            final, prov = await self._finalize_llm_reply(text, "apply_to_task", message, language, conf, tone)
            return AgentChatResponse(
                reply=final,
                intent="apply_to_task",
                suggested_actions=["view_task_details", "find_more_tasks"],
                tool_traces=traces,
                llm_provider=prov,
                **self._flags(conf),
            )

        if self._detect_publish_intent(message):
            text, trace = await self._tool_publish_draft_from_chat(db, user, message)
            traces.append(trace)
            conf = confidence_from_tool_trace(trace)
            final, prov = await self._finalize_llm_reply(text, "publish_draft", message, language, conf, tone)
            return AgentChatResponse(
                reply=final,
                intent="publish_draft",
                suggested_actions=["view_feed", "share_task_link"],
                tool_traces=traces,
                llm_provider=prov,
                **self._flags(conf),
            )

        if intent == "order_lookup":
            limit = self._extract_limit(message)
            text, trace = await self._tool_last_orders(db, user, limit)
            traces.append(trace)
            conf = confidence_from_tool_trace(trace)
            final, prov = await self._finalize_llm_reply(text, intent, message, language, conf, tone)
            return AgentChatResponse(
                reply=final,
                intent=intent,
                suggested_actions=["create_new_task", "view_task_details"],
                tool_traces=traces,
                llm_provider=prov,
                **self._flags(conf),
            )

        if intent == "task_discovery":
            text, trace = await self._tool_discovery(db, message)
            traces.append(trace)
            conf = confidence_from_tool_trace(trace)
            draft = text + "\nAap direct chatbot se apply bhi kar sakte ho (next step integration)."
            final, prov = await self._finalize_llm_reply(draft, intent, message, language, conf, tone)
            return AgentChatResponse(
                reply=final,
                intent=intent,
                suggested_actions=["apply_to_task", "refine_search"],
                tool_traces=traces,
                llm_provider=prov,
                **self._flags(conf),
            )

        if intent == "task_creation_assistant":
            if self._is_insufficient_task_description(message):
                text = (
                    "Bilkul, main task create karne me help karta hoon.\n"
                    "Please location, urgency, expected budget, aur kaam ka short description bhejo.\n"
                    "Example: 'create task: need plumber for kitchen tap leak in Indirapuram, budget 800'."
                )
                q_trace = AgentToolTrace(name="create_task_assistant", used=True, details="questionnaire_started")
                conf = confidence_from_tool_trace(q_trace)
                final, prov = await self._finalize_llm_reply(text, intent, message, language, conf, tone)
                return AgentChatResponse(
                    reply=final,
                    intent=intent,
                    follow_up_required=True,
                    suggested_actions=["describe_task_then_chat"],
                    tool_traces=[q_trace],
                    llm_provider=prov,
                    **self._flags(conf),
                )
            text, trace = await self._tool_create_task_draft_from_chat(db, user, message)
            traces = [trace]
            conf = confidence_from_tool_trace(trace)
            final, prov = await self._finalize_llm_reply(text, intent, message, language, conf, tone)
            return AgentChatResponse(
                reply=final,
                intent=intent,
                follow_up_required=False,
                suggested_actions=["publish_draft", "edit_draft_via_api"],
                tool_traces=traces,
                llm_provider=prov,
                **self._flags(conf),
            )

        text, trace, rag_scores = self._tool_rag_answer(message)
        traces.append(trace)
        conf = confidence_for_response(rag_scores, trace)
        final, prov = await self._finalize_llm_reply(text, intent, message, language, conf, tone)
        return AgentChatResponse(
            reply=final,
            intent=intent,
            suggested_actions=["refine_answer", "ask_followup"],
            tool_traces=traces,
            llm_provider=prov,
            **self._flags(conf),
        )

    @staticmethod
    def refine_answer(original: str, instruction: str, language: str) -> str:
        g = refine_with_gemini(
            original_answer=original, instruction=instruction, language=language, app_settings=settings
        )
        if g:
            return g
        ins = instruction.lower()
        if "short" in ins or "concise" in ins:
            return original[: min(len(original), 280)] + ("..." if len(original) > 280 else "")
        if "professional" in ins:
            return f"Professional summary:\n{original}"
        if language.lower() == "hi":
            return f"(Hindi preference)\n{original}"
        return f"Refined response ({instruction}):\n{original}"


agent_chat_service = AgentChatService()

