"""Detection -- shared helpers and Layer A (deterministic).

Layer A uses regex + format validators + checksums for high-precision
detection of structured identifiers (Requirement R2.1). Validators reduce
false positives (e.g. Luhn for credit cards).
"""
from __future__ import annotations

import re
from typing import Callable, Optional

from ..models import Category, Finding


def mask_preview(value: str) -> str:
    """Return a safe, masked preview of a value (never full raw value)."""
    v = str(value)
    if len(v) <= 2:
        return "*" * len(v)
    if len(v) <= 6:
        return v[0] + "*" * (len(v) - 2) + v[-1]
    return v[:2] + "*" * (len(v) - 4) + v[-2:]


# ---- validators ---------------------------------------------------------

def luhn_valid(number: str) -> bool:
    digits = [int(c) for c in re.sub(r"\D", "", number)]
    if len(digits) < 13:
        return False
    checksum = 0
    parity = len(digits) % 2
    for i, d in enumerate(digits):
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


def ssn_plausible(s: str) -> bool:
    digits = re.sub(r"\D", "", s)
    if len(digits) != 9:
        return False
    area, group, serial = digits[:3], digits[3:5], digits[5:]
    if area in ("000", "666") or area[0] == "9":
        return False
    if group == "00" or serial == "0000":
        return False
    return True


# ---- patterns -----------------------------------------------------------

class _Pattern:
    def __init__(
        self,
        entity_type: str,
        category: Category,
        regex: str,
        validator: Optional[Callable[[str], bool]] = None,
        score: float = 0.6,
        review_needed: bool = False,
    ) -> None:
        self.entity_type = entity_type
        self.category = category
        self.regex = re.compile(regex)
        self.validator = validator
        self.score = score
        self.review_needed = review_needed


_PATTERNS: list[_Pattern] = [
    _Pattern("EMAIL", Category.PII,
             r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b", score=0.95),
    _Pattern("CREDIT_CARD", Category.PII,
             r"\b(?:\d[ \-]?){13,19}\b", validator=luhn_valid, score=0.9),
    _Pattern("US_SSN", Category.PII,
             r"\b\d{3}-\d{2}-\d{4}\b", validator=ssn_plausible, score=0.85),
    _Pattern("PHONE", Category.PII,
             r"\b(?:\+?1[ \-.]?)?(?:\(?\d{3}\)?[ \-.]?)\d{3}[ \-.]?\d{4}\b",
             score=0.6, review_needed=True),
    _Pattern("IP_ADDRESS", Category.PII,
             r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b",
             score=0.7),
    _Pattern("IBAN", Category.PII,
             r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b", score=0.7, review_needed=True),
    _Pattern("URL", Category.SENSITIVE,
             r"\bhttps?://[^\s]+\b", score=0.5, review_needed=True),
    _Pattern("DATE_OF_BIRTH", Category.QUASI,
             r"\b(?:\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}"
             r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b",
             score=0.5, review_needed=True),
]


class DeterministicDetector:
    """Layer A."""

    name = "regex"

    def detect_text(
        self, text: str, field: Optional[str] = None, row: Optional[int] = None
    ) -> list[Finding]:
        findings: list[Finding] = []
        for pat in _PATTERNS:
            for m in pat.regex.finditer(text):
                raw = m.group(0)
                if pat.validator and not pat.validator(raw):
                    continue
                findings.append(
                    Finding(
                        entity_type=pat.entity_type,
                        category=pat.category,
                        source=f"regex:{pat.entity_type.lower()}",
                        sources=[f"regex:{pat.entity_type.lower()}"],
                        field=field,
                        row=row,
                        start=m.start(),
                        end=m.end(),
                        value_preview=mask_preview(raw),
                        score=pat.score,
                        review_needed=pat.review_needed,
                    )
                )
        return findings

    def detect_column(self, column: str, values: list[str]) -> list[Finding]:
        findings: list[Finding] = []
        for i, v in enumerate(values):
            findings.extend(self.detect_text(str(v), field=column, row=i))
        return findings
