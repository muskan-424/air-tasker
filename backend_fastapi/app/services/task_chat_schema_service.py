from __future__ import annotations

import re
from datetime import date, timedelta

from app.services.gemini_task_schema_service import build_task_schema_with_gemini, normalize_task_schema

_DATE_RE = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b")

# Checked in order — first match wins, so put more specific keywords ahead of generic
# ones (e.g. "electric" before the generic "repair"/"fix" that falls under handyman).
CATEGORY_KEYWORDS: list[tuple[str, list[str]]] = [
    ("plumbing", ["plumb", "pipe", "leak", "tap", "nal", "tank", "drain", "faucet"]),
    ("electrical", ["electric", "wiring", "fan", "bulb", "switch", "mcb", "inverter", "socket"]),
    ("cleaning", ["clean", "jhaadu", "dust", "mop", "sofa clean", "pest control"]),
    ("gardening", ["garden", "lawn", "plant", "mow", "landscap", "tree trim"]),
    ("painting", ["paint", "whitewash", "wall colour", "wall color"]),
    ("tech", ["tech", "laptop", "website", "code", "app", "software", "computer", "printer", "wifi", "router"]),
    ("moving", ["shift", "relocat", "movers", "packers", "moving", "delivery", "courier", "pickup and drop"]),
    ("tutoring", ["tutor", "tuition", "teach", "coaching", "homework", "exam prep"]),
    ("events", ["event", "photograph", "photo shoot", "decorat", "catering", "wedding", "party", " dj "]),
    ("handyman", ["repair", "assembly", "furniture", "fix", "install", "handyman", "drill", "mount", "wall"]),
]


def _detect_category(low: str) -> str:
    for category, keywords in CATEGORY_KEYWORDS:
        if any(kw in low for kw in keywords):
            return category
    return "general"


def _detect_location_type(low: str) -> str:
    if any(w in low for w in ["remote", "online", "video call", "phone call", "whatsapp", "wfh"]):
        return "REMOTE"
    return "IN_PERSON"


def _detect_timing(low: str) -> dict:
    """Best-effort date detection from free text; defaults to FLEXIBLE when nothing is found."""
    is_deadline = any(w in low for w in ["before", "by ", "deadline", "due"])

    if "today" in low or " aaj" in f" {low}":
        d = date.today()
    elif "tomorrow" in low or " kal" in f" {low}":
        d = date.today() + timedelta(days=1)
    else:
        m = _DATE_RE.search(low)
        if m:
            day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if year < 100:
                year += 2000
            try:
                d = date(year, month, day)
            except ValueError:
                d = None
        else:
            d = None

    if d is None:
        return {"type": "FLEXIBLE", "date": None}
    return {"type": "BEFORE_DATE" if is_deadline else "ON_DATE", "date": d.isoformat()}


def build_ai_schema_from_message(text: str) -> dict:
    """Infer structured task JSON from free-form chat (rule-based; Gemini can extend later)."""
    t = text.strip()
    low = t.lower()

    category = _detect_category(low)

    nums = [int(x) for x in re.findall(r"\b(\d{3,5})\b", t)]
    min_p, max_p = 500, 1200
    if len(nums) >= 2:
        a, b = sorted(nums[:2])
        min_p, max_p = a, b
    elif len(nums) == 1:
        n = nums[0]
        min_p = max(100, n - 200)
        max_p = n + 200

    title = t[:120] if len(t) > 120 else t
    non_ascii = sum(1 for c in t[:300] if ord(c) > 127)
    lang = "hi" if non_ascii > 5 else "en"

    urgency = "high" if any(w in low for w in ["urgent", "jaldi", "today", "aaj", "asap"]) else "normal"

    return {
        "title": title,
        "description": t,
        "language": lang,
        "category": category,
        "urgencyLevel": urgency,
        "locationType": _detect_location_type(low),
        "timing": _detect_timing(low),
        "suggestedPriceRange": {"min": min_p, "max": max_p, "currency": "INR"},
    }


def resolve_ai_schema(text: str, language: str | None = None) -> tuple[dict, str]:
    """Build task schema via Gemini when configured, else rule-based parser."""
    gemini_schema, provider = build_task_schema_with_gemini(text)
    if gemini_schema:
        schema = gemini_schema
    else:
        schema = normalize_task_schema(build_ai_schema_from_message(text), text)
        provider = "rule"
    if language:
        schema["language"] = language
    if provider == "gemini":
        from app.services.beta_service import record_gemini_call

        record_gemini_call()
    return schema, provider
