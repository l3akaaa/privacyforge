"""Data-utility comparison (Milestone 5; Requirement R6.2)."""
from __future__ import annotations

from statistics import mean, pstdev

from .models import Dataset, QualityReport


def _missing_counts(ds: Dataset) -> dict[str, int]:
    out: dict[str, int] = {}
    for col in ds.column_names:
        out[col] = sum(1 for r in ds.rows if r.get(col) in (None, "", "#NULL!"))
    return out


def _numeric_summary(ds: Dataset) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for c in ds.columns:
        if c.dtype != "number":
            continue
        vals = []
        for r in ds.rows:
            v = r.get(c.name)
            try:
                vals.append(float(v))
            except (TypeError, ValueError):
                continue
        if vals:
            out[c.name] = {
                "count": float(len(vals)),
                "mean": float(mean(vals)),
                "std": float(pstdev(vals)) if len(vals) > 1 else 0.0,
                "min": float(min(vals)),
                "max": float(max(vals)),
            }
    return out


def compare(before: Dataset, after: Dataset, changed_fields: list[str]) -> QualityReport:
    return QualityReport(
        rows_before=len(before.rows),
        rows_after=len(after.rows),
        columns_before=len(before.columns),
        columns_after=len(after.columns),
        missing_before=_missing_counts(before),
        missing_after=_missing_counts(after),
        changed_fields=sorted(set(changed_fields)),
        numeric_summary=_numeric_summary(after),
        possibly_broken_relationships=[],
    )
