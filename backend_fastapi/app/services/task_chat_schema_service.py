from __future__ import annotations

import re


def build_ai_schema_from_message(text: str) -> dict:
    """Infer structured task JSON from free-form chat (rule-based; Gemini can extend later)."""
    t = text.strip()
    low = t.lower()

    category = "general"
    if any(x in low for x in ["plumb", "pipe", "leak", "tap", "nal", "tank"]):
        category = "plumbing"
    elif any(x in low for x in ["electric", "wiring", "fan", "bulb", "switch"]):
        category = "electrical"
    elif any(x in low for x in ["clean", "jhaadu", "dust", "mop"]):
        category = "cleaning"
    elif any(x in low for x in ["tech", "laptop", "website", "code", "app", "software"]):
        category = "tech"
    elif any(x in low for x in ["paint", "wall", "repair", "handyman"]):
        category = "handyman"

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
        "suggestedPriceRange": {"min": min_p, "max": max_p, "currency": "INR"},
    }
