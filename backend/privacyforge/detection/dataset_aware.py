"""Layer C -- dataset-aware detection (Requirement R2.3).

Inspects column names, cardinality, and value format/prefix patterns to flag
likely identifiers that no built-in recognizer would catch (e.g. STU-2026-00421).
Uncertain columns are flagged review_needed rather than silently transformed.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Optional

from ..models import Category, Finding

# Column-name hints -> (entity_type, category). Configurable per project later.
_NAME_HINTS: dict[str, tuple[str, Category]] = {
    "student_id": ("STUDENT_ID", Category.PII),
    "student_number": ("STUDENT_ID", Category.PII),
    "studentid": ("STUDENT_ID", Category.PII),
    "employee_id": ("EMPLOYEE_ID", Category.PII),
    "patient_id": ("PATIENT_ID", Category.PII),
    "account_number": ("ACCOUNT_NUMBER", Category.PII),
    "id": ("RECORD_ID", Category.QUASI),
    "email": ("EMAIL", Category.PII),
    "phone": ("PHONE", Category.PII),
    "ssn": ("US_SSN", Category.PII),
    "dob": ("DATE_OF_BIRTH", Category.QUASI),
    "zip": ("ZIP_CODE", Category.QUASI),
    "zipcode": ("ZIP_CODE", Category.QUASI),
    "postal": ("POSTAL_CODE", Category.QUASI),
    "age": ("AGE", Category.QUASI),
    "name": ("PERSON", Category.PII),
}


def _normalize(col: str) -> str:
    return re.sub(r"[^a-z0-9]", "", col.lower())


def _modal_shape(values: list[str]) -> Optional[str]:
    """Return a regex-ish shape string if most values share one format."""
    shapes = Counter()
    for v in values:
        if not v:
            continue
        shape = re.sub(r"[A-Za-z]", "A", re.sub(r"\d", "9", v))
        shapes[shape] += 1
    if not shapes:
        return None
    top, count = shapes.most_common(1)[0]
    total = sum(shapes.values())
    if total and count / total >= 0.8 and len(shapes) <= max(3, total // 10):
        return top
    return None


class DatasetAwareDetector:
    """Layer C -- one finding per flagged column (whole-column signal)."""

    name = "column"

    def detect_column(self, column: str, values: list[str]) -> list[Finding]:
        norm = _normalize(column)
        non_empty = [v for v in values if v not in ("", "None", None)]
        if not non_empty:
            return []

        entity_type: Optional[str] = None
        category = Category.QUASI
        score = 0.3
        review = True

        # Signal 1: column-name hint.
        for hint, (etype, cat) in _NAME_HINTS.items():
            if hint == norm or hint in norm:
                entity_type, category = etype, cat
                score = 0.7
                review = cat == Category.QUASI
                break

        distinct = len(set(non_empty))
        cardinality = distinct / len(non_empty)
        shape = _modal_shape(non_empty)

        # Signal 2: high cardinality + consistent shape => likely identifier.
        if entity_type is None:
            if cardinality >= 0.9 and shape and re.search(r"A.*9|9.*A", shape):
                entity_type = "POSSIBLE_IDENTIFIER"
                category = Category.QUASI
                score = 0.55
                review = True
            else:
                return []
        else:
            if cardinality >= 0.9 and shape:
                score = min(0.9, score + 0.15)

        return [
            Finding(
                entity_type=entity_type,
                category=category,
                source="column",
                sources=["column"],
                field=column,
                row=None,
                value_preview=f"column '{column}' ({distinct} distinct, "
                              f"shape {shape or 'varied'})",
                score=score,
                review_needed=review,
                context=f"cardinality={cardinality:.2f}",
            )
        ]

    def detect_text(
        self, text: str, field: Optional[str] = None, row: Optional[int] = None
    ) -> list[Finding]:
        return []  # Layer C is column-level only.
