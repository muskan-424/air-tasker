import re

INDIA_PIN_RE = re.compile(r"^\d{6}$")


def normalize_india_pin(pin: str) -> str:
    """Validate and return a 6-digit India PIN code."""
    digits = re.sub(r"\D", "", pin or "")
    if not INDIA_PIN_RE.match(digits):
        raise ValueError("PIN must be a 6-digit India postal code")
    return digits


def normalize_pin_list(pins: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in pins:
        pin = normalize_india_pin(str(raw))
        if pin not in seen:
            seen.add(pin)
            out.append(pin)
    return out
