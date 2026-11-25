"""Phone-number check (public, no account).

POST /api/number  {input: "+971 …", lang: "en"|"ar"}
  → {kind: "number", input, number, digits, tag, verdict, score, reasons, scam_type, checks, offline_capable}

Deterministic, offline rules from the WS1 brain (`core/numbers.py`): premium-rate ranges, call-back /
VoIP allocations, same-digit repeats and a built-in pattern catalogue. Nothing is stored and nothing
is sent anywhere: a phone number is personal data.

`tag` follows the central rule that nothing unknown is SAFE: MALICIOUS → FAKE, SUSPICIOUS → WARNING,
no signs → WARNING ("not verified" — absence of warning signs is not proof the number is safe).
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .. import security
from ..core import numbers

router = APIRouter()

# Stable codes for each rule family (clients translate these; `reasons` keep the engine's detail).
SIGN_CODES = (
    ("reported-number pattern", "pattern_catalogue"),
    ("premium", "premium_rate"),
    ("VoIP", "callback_voip"),
    ("callback", "callback_voip"),
    ("same-digit repeat", "digit_repeat"),
)


def _signs(reasons: list[str]) -> list[dict]:
    out = []
    for reason in reasons:
        code = next((c for needle, c in SIGN_CODES if needle.lower() in reason.lower()), None)
        if code:
            out.append({"code": code, "detail": reason})
    return out


TAGS = {"MALICIOUS": "FAKE", "MISLEADING": "MISLEADING", "SUSPICIOUS": "WARNING", "UNKNOWN": "WARNING"}
MIN_DIGITS, MAX_DIGITS = 6, 15          # E.164 allows up to 15 digits


class NumberRequest(BaseModel):
    input: str = Field(min_length=1, max_length=40)
    lang: Literal["en", "ar"] = "en"


@router.post("/api/number")
async def check_number(payload: NumberRequest, request: Request):
    rt = request.app.state.runtime
    ip = security.client_ip(request, rt.settings.trust_proxy_headers)
    if not rt.scan_limiter.hit(ip):
        raise HTTPException(status_code=429, detail={"code": "rate_limited", "message": "too many checks — wait a minute"})
    raw = payload.input.strip()
    if any(ch.isalpha() for ch in raw):
        raise HTTPException(status_code=422, detail={"code": "invalid_number",
                                                     "message": "enter a phone number (digits, spaces, + or -)"})
    digits = numbers.normalize_number(raw)
    if not (MIN_DIGITS <= len(digits) <= MAX_DIGITS):
        raise HTTPException(status_code=422, detail={"code": "invalid_number",
                                                     "message": f"a phone number has {MIN_DIGITS}–{MAX_DIGITS} digits"})
    result = numbers.check_number(raw)
    signs = result.verdict != "UNKNOWN"
    return {
        "kind": "number",
        "input": raw,
        "number": ("+" + digits) if raw.lstrip().startswith(("+", "00")) else digits,
        "digits": digits,
        "tag": TAGS.get(result.verdict, "WARNING"),
        "verdict": result.verdict,
        "score": result.score,
        "reasons": list(result.reasons),
        "scam_type": result.scam_type,
        "warning_signs": signs,
        "signs": _signs(list(result.reasons)) if signs else [],
        "checks": [{"id": "number_rules", "status": "completed",
                    "summary": "offline number-pattern rules (premium-rate, call-back/VoIP, repeats, pattern catalogue)"}],
        "stored": False,
        "offline_capable": result.offline_capable,
    }
