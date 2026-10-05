"""Heuristic PII detection and optional SHA-256 tokenization.

This is regex-pattern matching on column content, nothing more. It is
explicitly NOT a claim of legal compliance (GDPR/CCPA/HIPAA etc.) — label
every result "Heuristic Detection" in the UI, per the project rules.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Dict, List

import pandas as pd

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2})?)?$")


def _looks_like_phone(value: str) -> bool:
    """A digit-and-separator string shaped like a phone number.

    The naive version of this (any run of 8-16 digits/separators) also
    matched ISO date strings like "2025-03-15", which have exactly the same
    shape — flagging every date column as PII. Dates have exactly 8 digits;
    real phone numbers (with or without a country code) have 9+.
    """
    if not re.match(r"^\+?\d[\d\-\.\s()]{7,14}\d$", value):
        return False
    if _ISO_DATE_RE.match(value):
        return False
    digit_count = sum(1 for c in value if c.isdigit())
    return digit_count >= 9


_PATTERNS = {
    "email": re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$"),
    "phone_number": _looks_like_phone,
    "ssn_like": re.compile(r"^\d{3}-\d{2}-\d{4}$"),
    "credit_card_like": re.compile(r"^\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}$"),
    "ip_address": re.compile(r"^(\d{1,3}\.){3}\d{1,3}$"),
}

_NAME_HINTS = {
    "email": ("email", "e_mail", "mail"),
    "phone_number": ("phone", "mobile", "cell", "contact_number"),
    "ssn_like": ("ssn", "social_security"),
    "credit_card_like": ("card", "credit_card", "cc_number"),
    "ip_address": ("ip_address", "ip"),
}


@dataclass
class PIIDetectionResult:
    column: str
    pattern: str
    match_count: int
    match_pct: float
    sample_masked: List[str] = field(default_factory=list)
    detection_method: str = "Heuristic Detection (regex pattern match)"


def _mask(value: str) -> str:
    value = str(value)
    if len(value) <= 4:
        return "*" * len(value)
    return value[:2] + "*" * (len(value) - 4) + value[-2:]


def _matches(matcher, value: str) -> bool:
    """matcher is either a compiled regex (has .match) or a plain predicate callable."""
    if hasattr(matcher, "match"):
        return bool(matcher.match(value))
    return bool(matcher(value))


def detect_pii(df: pd.DataFrame) -> List[PIIDetectionResult]:
    results = []
    for col in df.columns:
        s = df[col].dropna().astype(str)
        if s.empty:
            continue
        sample = s.sample(min(len(s), 500), random_state=0)
        col_lower = col.lower()
        for pattern_name, matcher in _PATTERNS.items():
            name_bonus = any(hint in col_lower for hint in _NAME_HINTS.get(pattern_name, ()))
            matches = sample.apply(lambda v: _matches(matcher, v.strip()))
            match_rate = matches.mean()
            if match_rate >= 0.6 or (name_bonus and match_rate >= 0.2):
                full_matches = s.apply(lambda v: _matches(matcher, v.strip()))
                count = int(full_matches.sum())
                results.append(PIIDetectionResult(
                    column=col, pattern=pattern_name, match_count=count,
                    match_pct=round(100 * count / len(df), 4),
                    sample_masked=[_mask(v) for v in s[full_matches].head(3)],
                ))
    return results


def tokenize_column(df: pd.DataFrame, column: str, salt: str = "") -> pd.DataFrame:
    """Returns a copy with `column` replaced by SHA-256 tokens. Same input -> same
    token every time (referential consistency), so joins on the tokenized column
    still work after tokenization."""
    out = df.copy()

    def _hash(v):
        if pd.isna(v):
            return v
        return hashlib.sha256(f"{salt}{v}".encode("utf-8")).hexdigest()

    out[column] = out[column].apply(_hash)
    return out
