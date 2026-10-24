"""Policy engine (Milestone 4; Requirements R3.2, R3.3).

A Policy is an ordered list of rules mapping an entity type, column, or category
to a transform operator. Presets are starting configurations, NOT compliance
certifications -- every preset carries that disclaimer.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from .models import Finding

Operator = Literal["redact", "mask", "tokenize", "synthetic", "generalize", "retain"]


class PolicyRule(BaseModel):
    match_type: Literal["entity", "column", "category"]
    match_value: str                    # entity type, column name, or category
    operator: Operator
    params: dict = Field(default_factory=dict)


class Policy(BaseModel):
    name: str = "custom"
    rules: list[PolicyRule] = Field(default_factory=list)
    default_operator: Operator = "redact"
    disclaimer: str = (
        "This policy is a starting configuration, not a legal-compliance "
        "certification. Review it against your own requirements."
    )

    def resolve(self, finding: Finding) -> tuple[Operator, dict]:
        # Precedence: explicit column rule > entity rule > category rule > default.
        for mt in ("column", "entity", "category"):
            for rule in self.rules:
                if rule.match_type != mt:
                    continue
                if mt == "column" and finding.field == rule.match_value:
                    return rule.operator, rule.params
                if mt == "entity" and finding.entity_type == rule.match_value:
                    return rule.operator, rule.params
                if mt == "category" and finding.category.value == rule.match_value:
                    return rule.operator, rule.params
        return self.default_operator, {}


def _rule(mt: str, val: str, op: Operator, **params) -> PolicyRule:
    return PolicyRule(match_type=mt, match_value=val, operator=op, params=params)  # type: ignore[arg-type]


PRESETS: dict[str, Policy] = {
    "recommended": Policy(
        name="recommended",
        rules=[
            # Identifiers -> secure tokens (reversible only via the vault).
            _rule("entity", "STUDENT_ID", "tokenize"),
            _rule("entity", "RECORD_ID", "tokenize"),
            _rule("entity", "POSSIBLE_IDENTIFIER", "tokenize"),
            _rule("entity", "ACCOUNT_NUMBER", "tokenize"),
            # Direct identifiers -> removed.
            _rule("category", "pii", "redact"),
            # Sensitive -> removed.
            _rule("category", "sensitive", "redact"),
            # Quasi-identifiers -> blurred (age ranges, year-only dates, zip prefix).
            _rule("category", "quasi", "generalize"),
        ],
        default_operator="redact",
        disclaimer=(
            "Recommended safe defaults: identifiers are tokenized, direct and "
            "sensitive values are removed, and quasi-identifiers are generalized. "
            "This is a starting configuration, not a legal-compliance certification. "
            "Always review the verification report before trusting an export."
        ),
    ),
    "academic_research": Policy(
        name="academic_research",
        rules=[
            _rule("entity", "STUDENT_ID", "tokenize"),
            _rule("entity", "RECORD_ID", "tokenize"),
            _rule("entity", "POSSIBLE_IDENTIFIER", "tokenize"),
            _rule("entity", "EMAIL", "redact"),
            _rule("entity", "PERSON", "synthetic"),
            _rule("entity", "DATE_OF_BIRTH", "generalize", mode="year"),
            _rule("category", "quasi", "generalize"),
        ],
        default_operator="redact",
    ),
    "student_records": Policy(
        name="student_records",
        rules=[
            _rule("entity", "STUDENT_ID", "tokenize"),
            _rule("entity", "RECORD_ID", "tokenize"),
            _rule("entity", "POSSIBLE_IDENTIFIER", "tokenize"),
            _rule("entity", "EMAIL", "redact"),
            _rule("entity", "PHONE", "redact"),
            _rule("entity", "PERSON", "redact"),
        ],
        default_operator="redact",
    ),
    "business_analytics": Policy(
        name="business_analytics",
        rules=[
            _rule("category", "pii", "tokenize"),
            _rule("category", "sensitive", "redact"),
            _rule("category", "quasi", "retain"),
        ],
        default_operator="mask",
    ),
    "ai_prompt_protection": Policy(
        name="ai_prompt_protection",
        rules=[
            _rule("category", "pii", "redact"),
            _rule("category", "sensitive", "redact"),
        ],
        default_operator="redact",
    ),
    "software_testing": Policy(
        name="software_testing",
        rules=[
            _rule("category", "pii", "synthetic"),
            _rule("entity", "STUDENT_ID", "tokenize"),
        ],
        default_operator="synthetic",
    ),
}


def get_preset(name: str) -> Optional[Policy]:
    preset = PRESETS.get(name)
    return preset.model_copy(deep=True) if preset else None
