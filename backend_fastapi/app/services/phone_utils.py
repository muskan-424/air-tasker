import re

INDIA_MOBILE_RE = re.compile(r"^[6-9]\d{9}$")


def normalize_india_phone(phone: str) -> str:
    """Validate and return a 10-digit India mobile number (strips +91/91/0/spaces/dashes)."""
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if not INDIA_MOBILE_RE.match(digits):
        raise ValueError("Enter a valid 10-digit India mobile number")
    return digits


def to_e164_india(phone_10_digit: str) -> str:
    return f"+91{phone_10_digit}"
