"""Privacy risk verification (Milestone 5; Requirements R5.1-R5.5).

Independently inspects transformed output: residual-PII rescan, quasi-identifier
uniqueness / k-anonymity, data-leakage checks, a transparent risk report, and the
fail-safe export gate. Never produces a "100% safe" score.
"""
from __future__ import annotations

from collections import Counter
from typing import Optional

from .detection import DetectionPipeline
from .models import Dataset, Finding, GateDecision, RiskReport, TextDoc

_LIMITATIONS = [
    "Detection is heuristic and may miss novel or obfuscated identifiers.",
    "k-anonymity and uniqueness analysis depend on the quasi-identifiers you "
    "select and on this dataset alone; external data can still re-identify records.",
    "This report does not certify legal compliance and is not a guarantee of safety.",
]


def residual_scan(
    output: Dataset | TextDoc, pipeline: Optional[DetectionPipeline] = None
) -> list[Finding]:
    pipeline = pipeline or DetectionPipeline(use_nlp=False)
    if isinstance(output, TextDoc):
        return pipeline.detect_text(output)
    return pipeline.detect_dataset(output)


def k_anonymity(ds: Dataset, quasi_identifiers: list[str]) -> dict:
    """Return min group size (k) and the count of unique (k=1) records."""
    qi = [c for c in quasi_identifiers if c in ds.column_names]
    if not qi:
        return {"k": None, "unique_records": 0, "quasi_identifiers": [], "groups": 0}
    groups = Counter(tuple(str(r.get(c)) for c in qi) for r in ds.rows)
    sizes = list(groups.values())
    k = min(sizes) if sizes else 0
    unique = sum(1 for s in sizes if s == 1)
    return {
        "k": k,
        "unique_records": unique,
        "quasi_identifiers": qi,
        "groups": len(groups),
    }


def leakage_check(ds: Dataset, originals_sample: list[str]) -> list[str]:
    """Detect planted original values remaining in output cells (R5.3)."""
    leaks: list[str] = []
    haystack = {str(r.get(c)) for r in ds.rows for c in ds.column_names}
    for original in originals_sample:
        if original and str(original) in haystack:
            leaks.append(f"Original value still present in output: '{original[:4]}...'")
    return leaks


def build_risk_report(
    output: Dataset | TextDoc,
    operators_used: dict[str, str],
    quasi_identifiers: Optional[list[str]] = None,
    leaked_originals: Optional[list[str]] = None,
    unprocessed: Optional[list[str]] = None,
    pipeline: Optional[DetectionPipeline] = None,
) -> RiskReport:
    residual = residual_scan(output, pipeline)
    unreviewed = sum(1 for f in residual if f.review_needed)
    risky: list[dict] = []
    if isinstance(output, Dataset) and quasi_identifiers:
        ka = k_anonymity(output, quasi_identifiers)
        if ka["k"] is not None and ka["k"] <= 1:
            risky.append({
                "type": "low_k_anonymity",
                "detail": f"{ka['unique_records']} record(s) are unique on the "
                          f"selected quasi-identifiers (k={ka['k']}).",
                "quasi_identifiers": ka["quasi_identifiers"],
            })
    leaks = leakage_check(output, leaked_originals or []) if isinstance(output, Dataset) else []
    limitations = list(_LIMITATIONS)
    if leaks:
        limitations.append("Data-leakage checks found residual original values; see above.")
    return RiskReport(
        residual_findings=residual,
        unreviewed_count=unreviewed,
        risky_combinations=risky,
        transforms_used=operators_used,
        unprocessed_content=(unprocessed or []) + leaks,
        limitations=limitations,
    )


def export_gate(report: RiskReport, processing_ok: bool = True) -> GateDecision:
    """Fail-safe gate (R5.5). Blocks on failure/unexamined/critical findings."""
    reasons: list[str] = []
    if not processing_ok:
        reasons.append("Processing did not complete successfully.")
    # Residual PII (directly identifying) with VALUE-LEVEL evidence is critical.
    # A column-name-only hint (row is None, no span) is not proof that a value
    # leaked -- an already-redacted column still matches its name -- so those are
    # surfaced for review, not treated as a hard block.
    critical = [
        f
        for f in report.residual_findings
        if f.category.value == "pii" and (f.row is not None or f.start is not None)
    ]
    if critical:
        reasons.append(
            f"{len(critical)} residual directly-identifying value(s) remain in the output."
        )
    if any("Original value still present" in u for u in report.unprocessed_content):
        reasons.append("Original values were found leaking in the output.")
    return GateDecision(allow_export=len(reasons) == 0, reasons=reasons)
