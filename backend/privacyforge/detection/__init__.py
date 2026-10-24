"""Detection pipeline orchestrator (Layers A-F)."""
from __future__ import annotations

from typing import Optional

from ..models import Dataset, Finding, TextDoc
from .aggregation import aggregate
from .custom_rules import CustomRule, CustomRuleDetector, dry_run_rule
from .dataset_aware import DatasetAwareDetector
from .deterministic import DeterministicDetector
from .nlp import NlpDetector

__all__ = [
    "DetectionPipeline",
    "CustomRule",
    "dry_run_rule",
]


class DetectionPipeline:
    """Runs all enabled detection layers and aggregates the result.

    `use_nlp` defaults to True but silently no-ops if Presidio/spaCy are not
    installed (the adapter reports availability).
    """

    def __init__(
        self,
        custom_rules: Optional[list[CustomRule]] = None,
        use_nlp: bool = True,
    ) -> None:
        self.deterministic = DeterministicDetector()
        self.dataset_aware = DatasetAwareDetector()
        self.custom = CustomRuleDetector(custom_rules or [])
        self.nlp = NlpDetector() if use_nlp else None

    @property
    def nlp_available(self) -> bool:
        return bool(self.nlp and self.nlp.available)

    def detect_text(self, doc: TextDoc) -> list[Finding]:
        findings: list[Finding] = []
        findings += self.deterministic.detect_text(doc.text)
        findings += self.custom.detect_text(doc.text)
        if self.nlp:
            findings += self.nlp.detect_text(doc.text)
        return aggregate(findings)

    def detect_dataset(self, ds: Dataset) -> list[Finding]:
        findings: list[Finding] = []
        for col in ds.column_names:
            values = ds.column_values(col)
            findings += self.deterministic.detect_column(col, values)
            findings += self.dataset_aware.detect_column(col, values)
            findings += self.custom.detect_column(col, values)
            # NLP only on free-text (string) columns to control cost.
            if self.nlp:
                schema = next((c for c in ds.columns if c.name == col), None)
                if schema and schema.dtype in ("string", "mixed"):
                    findings += self.nlp.detect_column(col, values)
        return aggregate(findings)
