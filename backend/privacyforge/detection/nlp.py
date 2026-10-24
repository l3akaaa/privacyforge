"""Layer B -- NLP detection via Presidio + spaCy (Requirement R2.2).

This layer is OPTIONAL at runtime. If presidio/spaCy (and the model) are not
installed, the adapter reports `available = False` and returns no findings,
so the rest of the pipeline keeps working. This realizes the design's
"detectors are swappable plugins" rule.
"""
from __future__ import annotations

from typing import Optional

from .deterministic import mask_preview
from ..models import Category, Finding

# Presidio label -> our (entity_type, category)
_LABEL_MAP: dict[str, tuple[str, Category]] = {
    "PERSON": ("PERSON", Category.PII),
    "LOCATION": ("LOCATION", Category.QUASI),
    "GPE": ("LOCATION", Category.QUASI),
    "NRP": ("NRP", Category.SENSITIVE),
    "ORGANIZATION": ("ORGANIZATION", Category.SENSITIVE),
    "ORG": ("ORGANIZATION", Category.SENSITIVE),
    "DATE_TIME": ("DATE_TIME", Category.QUASI),
}


class NlpDetector:
    name = "nlp"

    def __init__(self) -> None:
        self._engine = None
        self.available = False
        try:
            from presidio_analyzer import AnalyzerEngine  # type: ignore

            self._engine = AnalyzerEngine()
            self.available = True
        except Exception:  # pragma: no cover - depends on optional install
            self._engine = None
            self.available = False

    def _context(self, text: str, start: int, end: int, window: int = 30) -> str:
        lo = max(0, start - window)
        hi = min(len(text), end + window)
        return text[lo:hi]

    def detect_text(
        self, text: str, field: Optional[str] = None, row: Optional[int] = None
    ) -> list[Finding]:
        if not self.available or not text.strip():
            return []
        try:
            results = self._engine.analyze(text=text, language="en")  # type: ignore
        except Exception:  # pragma: no cover
            return []
        findings: list[Finding] = []
        for r in results:
            etype, category = _LABEL_MAP.get(r.entity_type, (r.entity_type, Category.PII))
            raw = text[r.start : r.end]
            findings.append(
                Finding(
                    entity_type=etype,
                    category=category,
                    source=f"presidio:{r.entity_type}",
                    sources=[f"presidio:{r.entity_type}"],
                    field=field,
                    row=row,
                    start=r.start,
                    end=r.end,
                    value_preview=mask_preview(raw),
                    score=float(r.score),
                    context=self._context(text, r.start, r.end),
                    review_needed=r.score < 0.6,
                )
            )
        return findings

    def detect_column(self, column: str, values: list[str]) -> list[Finding]:
        if not self.available:
            return []
        findings: list[Finding] = []
        for i, v in enumerate(values):
            findings.extend(self.detect_text(str(v), field=column, row=i))
        return findings
