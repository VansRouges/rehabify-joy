import re

from fastapi import Request


def normalize_phone(raw: str) -> str:
    """Normalize to E.164. Defaults Nigerian (+234) numbers."""
    digits = re.sub(r"\D", "", raw.strip())

    if raw.strip().startswith("+"):
        return f"+{digits}"

    if digits.startswith("234") and len(digits) >= 13:
        return f"+{digits}"

    if digits.startswith("0") and len(digits) == 11:
        return f"+234{digits[1:]}"

    if len(digits) == 10:
        return f"+234{digits}"

    if digits.startswith("234"):
        return f"+{digits}"

    return f"+{digits}"


def is_valid_phone(raw: str) -> bool:
    normalized = normalize_phone(raw)
    return bool(re.fullmatch(r"\+\d{10,15}", normalized))


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
