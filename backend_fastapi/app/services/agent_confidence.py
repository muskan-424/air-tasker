from __future__ import annotations

from app.schemas.chat import AgentToolTrace


def _norm_score(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def confidence_from_rag_scores(scores: list[float]) -> float:
    """Average normalized retrieval scores; empty = low confidence."""
    if not scores:
        return 0.32
    return sum(_norm_score(s) for s in scores) / len(scores)


def confidence_from_tool_trace(trace: AgentToolTrace) -> float:
    """Heuristic confidence from deterministic tool outcomes."""
    name = trace.name
    d = (trace.details or "").lower()

    if name == "get_user_orders":
        if "no_records" in d:
            return 0.42
        return 0.88

    if name == "search_tasks":
        if "no_matches" in d:
            return 0.4
        return 0.86

    if name == "apply_to_task":
        if "applied" in d:
            return 0.95
        if "already_applied" in d:
            return 0.88
        if "role_not_tasker" in d or "missing_task_id" in d or "invalid_task_id" in d:
            return 0.35
        if "task_not_found" in d or "status=" in d:
            return 0.4
        return 0.45

    if name == "publish_draft":
        if "task_id=" in d and "error=" not in d:
            return 0.92
        if "no_draft" in d:
            return 0.38
        if "error=" in d:
            return 0.35
        return 0.45

    if name == "create_task_draft":
        if "draft_id=" in d:
            return 0.87
        return 0.5

    if name == "create_task_assistant" and "questionnaire" in d:
        return 0.55

    if name == "rag_lookup":
        if "rag=none" in d or "fallback" in d:
            return 0.38
        return 0.72

    return 0.65


def confidence_for_response(rag_scores: list[float] | None, trace: AgentToolTrace) -> float:
    """Prefer RAG scores when present; else tool trace."""
    if rag_scores:
        return confidence_from_rag_scores(rag_scores)
    return confidence_from_tool_trace(trace)
