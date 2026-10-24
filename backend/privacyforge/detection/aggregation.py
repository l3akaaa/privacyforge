"""Layer F -- aggregation (Requirement R2.7, R2.8).

Merges overlapping detections within the same field+row span, keeps all source
detectors, resolves the label by a precedence order, and preserves review flags.
"""
from __future__ import annotations

from ..models import Finding

# Label precedence when two detectors overlap (higher = wins the label).
_PRECEDENCE = {
    "regex": 4,
    "custom": 3,
    "presidio": 2,
    "nlp": 2,
    "column": 1,
}


def _rank(source: str) -> int:
    key = source.split(":", 1)[0]
    return _PRECEDENCE.get(key, 0)


def _overlaps(a: Finding, b: Finding) -> bool:
    if a.field != b.field or a.row != b.row:
        return False
    if a.start is None or b.start is None:
        # Column-level (no span) findings on the same field overlap.
        return a.start is None and b.start is None
    return a.start < (b.end or b.start) and b.start < (a.end or a.start)


def aggregate(findings: list[Finding]) -> list[Finding]:
    merged: list[Finding] = []
    for f in sorted(findings, key=lambda x: (str(x.field), x.row or -1, x.start or -1)):
        placed = False
        for m in merged:
            if _overlaps(f, m):
                # Merge: keep union of sources; label from higher precedence.
                for s in f.sources or [f.source]:
                    if s not in m.sources:
                        m.sources.append(s)
                if _rank(f.source) > _rank(m.source):
                    m.entity_type = f.entity_type
                    m.category = f.category
                    m.source = f.source
                    m.score = f.score
                m.review_needed = m.review_needed or f.review_needed
                if f.context and not m.context:
                    m.context = f.context
                placed = True
                break
        if not placed:
            merged.append(f.model_copy(deep=True))
    return merged
