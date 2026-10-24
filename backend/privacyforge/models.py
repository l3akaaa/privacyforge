"""Core typed models shared across modules.

These models are the contract between detection, aggregation, policy,
transform, verification and the API. Keep them free of web/framework code.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class Category(str, Enum):
    """Sensitivity classes (Requirement R2.4)."""

    PII = "pii"            # directly identifying
    SENSITIVE = "sensitive"  # confidential but not directly identifying
    QUASI = "quasi"        # quasi-identifier (identifying in combination)


class Finding(BaseModel):
    """A single detection. Produced by detectors, merged by aggregation.

    Guarantees: `value_preview` is masked and safe to log/display. The raw
    original value is NEVER stored on a Finding.
    """

    entity_type: str
    category: Category
    source: str                       # e.g. "regex:email", "column", "custom:<id>", "spacy"
    field: Optional[str] = None       # column name for structured data
    row: Optional[int] = None         # row index for structured data
    start: Optional[int] = None       # char span start (text)
    end: Optional[int] = None         # char span end (text)
    value_preview: str = ""           # masked preview only
    score: Optional[float] = None     # raw, uncalibrated detector score 0..1
    context: Optional[str] = None     # surrounding snippet (NLP)
    review_needed: bool = False
    sources: list[str] = Field(default_factory=list)  # all merged sources

    def span_key(self) -> tuple[Any, ...]:
        """Identity used for overlap/dedup within a field+row."""
        return (self.field, self.row, self.start, self.end)


class ColumnSchema(BaseModel):
    name: str
    dtype: Literal["string", "number", "boolean", "mixed"] = "string"


class Dataset(BaseModel):
    """Structured tabular data (CSV/XLSX/JSON-of-records)."""

    columns: list[ColumnSchema]
    rows: list[dict[str, Any]]
    kind: Literal["csv", "xlsx", "json"] = "csv"

    @property
    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]

    def column_values(self, name: str) -> list[str]:
        return ["" if r.get(name) is None else str(r.get(name)) for r in self.rows]


class TextDoc(BaseModel):
    """Unstructured text document (TXT)."""

    text: str
    kind: Literal["txt"] = "txt"


class RiskReport(BaseModel):
    residual_findings: list[Finding] = Field(default_factory=list)
    unreviewed_count: int = 0
    risky_combinations: list[dict[str, Any]] = Field(default_factory=list)
    transforms_used: dict[str, str] = Field(default_factory=dict)  # entity/col -> operator
    unprocessed_content: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    # Deliberately NO "overall_safe" / "percent_safe" field (R5.4).


class QualityReport(BaseModel):
    rows_before: int = 0
    rows_after: int = 0
    columns_before: int = 0
    columns_after: int = 0
    missing_before: dict[str, int] = Field(default_factory=dict)
    missing_after: dict[str, int] = Field(default_factory=dict)
    changed_fields: list[str] = Field(default_factory=list)
    numeric_summary: dict[str, dict[str, float]] = Field(default_factory=dict)
    possibly_broken_relationships: list[str] = Field(default_factory=list)


class GateDecision(BaseModel):
    allow_export: bool
    reasons: list[str] = Field(default_factory=list)
