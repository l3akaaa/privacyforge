"""Layer E -- user-defined custom rules (Requirement R2.6).

Supports custom regex, sensitive column names, protected keyword dictionaries,
and org-specific id formats -- all without code. Includes a dry-run test so a
rule can be checked against sample data before being applied.
"""
from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel

from .deterministic import mask_preview
from ..models import Category, Finding


class CustomRule(BaseModel):
    id: str
    entity_type: str
    category: Category = Category.SENSITIVE
    kind: Literal["regex", "column_name", "keyword"] = "regex"
    pattern: str                 # regex, column name, or keyword/term
    score: float = 0.6
    review_needed: bool = False


class CustomRuleDetector:
    name = "custom"

    def __init__(self, rules: Optional[list[CustomRule]] = None) -> None:
        self.rules = rules or []

    def _regex_rules(self) -> list[tuple[CustomRule, re.Pattern[str]]]:
        out = []
        for r in self.rules:
            if r.kind in ("regex", "keyword"):
                pat = r.pattern if r.kind == "regex" else re.escape(r.pattern)
                out.append((r, re.compile(pat, re.IGNORECASE if r.kind == "keyword" else 0)))
        return out

    def detect_text(
        self, text: str, field: Optional[str] = None, row: Optional[int] = None
    ) -> list[Finding]:
        findings: list[Finding] = []
        for rule, pat in self._regex_rules():
            for m in pat.finditer(text):
                findings.append(
                    Finding(
                        entity_type=rule.entity_type,
                        category=rule.category,
                        source=f"custom:{rule.id}",
                        sources=[f"custom:{rule.id}"],
                        field=field,
                        row=row,
                        start=m.start(),
                        end=m.end(),
                        value_preview=mask_preview(m.group(0)),
                        score=rule.score,
                        review_needed=rule.review_needed,
                    )
                )
        return findings

    def detect_column(self, column: str, values: list[str]) -> list[Finding]:
        findings: list[Finding] = []
        norm = column.strip().lower()
        for rule in self.rules:
            if rule.kind == "column_name" and rule.pattern.strip().lower() == norm:
                findings.append(
                    Finding(
                        entity_type=rule.entity_type,
                        category=rule.category,
                        source=f"custom:{rule.id}",
                        sources=[f"custom:{rule.id}"],
                        field=column,
                        value_preview=f"column '{column}' matched custom rule",
                        score=rule.score,
                        review_needed=rule.review_needed,
                    )
                )
        for i, v in enumerate(values):
            findings.extend(self.detect_text(str(v), field=column, row=i))
        return findings


def dry_run_rule(rule: CustomRule, sample: str) -> list[dict[str, object]]:
    """Dry-run a rule against sample text; returns match spans (R2.6)."""
    det = CustomRuleDetector([rule])
    return [
        {"start": f.start, "end": f.end, "preview": f.value_preview}
        for f in det.detect_text(sample)
    ]
