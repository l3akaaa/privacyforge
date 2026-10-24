"""Benchmark suite (Section 13): labeled synthetic scenarios -> precision/recall/F1.

Each scenario is text with KNOWN expected entity types. We run the detection
pipeline and compare. Results are reported honestly; the 95% recall target
applies ONLY to this controlled synthetic benchmark, never real-world data.

Run:  python -m privacyforge.benchmark
"""
from __future__ import annotations

from dataclasses import dataclass

from .detection import CustomRule, DetectionPipeline


@dataclass
class Scenario:
    name: str
    text: str
    expected: set[str]          # entity types expected somewhere in the text
    custom_rules: list[CustomRule] | None = None
    column: tuple[str, list[str]] | None = None  # (column_name, values) for Layer C
    needs_nlp: bool = False


SCENARIOS: list[Scenario] = [
    Scenario("1_email_phone", "Email jane@uni.edu or call 415-555-0199.",
             {"EMAIL", "PHONE"}),
    Scenario("2_name_in_sentence", "Professor Maria Gonzalez taught the seminar.",
             {"PERSON"}, needs_nlp=True),
    Scenario("3_org_student_id", "", {"STUDENT_ID"},
             column=("student_id", [f"STU-2026-{i:05d}" for i in range(20)])),
    Scenario("7_id_without_label", "Record BDG-4471 flagged.",
             {"BADGE"}, [CustomRule(id="badge", entity_type="BADGE", pattern=r"BDG-\d{4}")]),
    Scenario("8_benign_lookalike", "Order number 1234 5678 9012 3456 shipped.",
             set()),  # invalid Luhn -> must NOT be flagged as CREDIT_CARD
    Scenario("1_ssn", "SSN 123-45-6789 on file.", {"US_SSN"}),
    Scenario("1_credit_card", "Card 4111 1111 1111 1111 charged.", {"CREDIT_CARD"}),
    Scenario("1_ip", "Server at 192.168.10.5 responded.", {"IP_ADDRESS"}),
]


def _run_scenario(sc: Scenario, pipe: DetectionPipeline) -> tuple[set[str], set[str]]:
    from .models import TextDoc

    p = pipe
    if sc.custom_rules:
        p = DetectionPipeline(custom_rules=sc.custom_rules, use_nlp=pipe.nlp is not None)
    if sc.column is not None:
        from .models import ColumnSchema, Dataset

        name, values = sc.column
        ds = Dataset(columns=[ColumnSchema(name=name, dtype="string")],
                     rows=[{name: v} for v in values], kind="csv")
        findings = p.detect_dataset(ds)
    else:
        findings = p.detect_text(TextDoc(text=sc.text))
    found = {f.entity_type for f in findings}
    return found, sc.expected


def run(use_nlp: bool = True) -> dict:
    pipe = DetectionPipeline(use_nlp=use_nlp)
    tp = fp = fn = 0
    per_type: dict[str, dict[str, int]] = {}
    rows = []
    for sc in SCENARIOS:
        found, expected = _run_scenario(sc, pipe)
        s_tp = len(found & expected)
        s_fn = len(expected - found)
        # Count only "relevant" false positives (known entity universe).
        universe = expected | {"EMAIL", "PHONE", "US_SSN", "CREDIT_CARD", "IP_ADDRESS", "BADGE"}
        s_fp = len((found & universe) - expected)
        tp += s_tp
        fp += s_fp
        fn += s_fn
        for et in expected:
            d = per_type.setdefault(et, {"tp": 0, "fn": 0})
            if et in found:
                d["tp"] += 1
            else:
                d["fn"] += 1
        rows.append({"scenario": sc.name, "expected": sorted(expected),
                     "found": sorted(found), "tp": s_tp, "fp": s_fp, "fn": s_fn})

    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    # Recall excluding scenarios that require the optional NLP layer, so the
    # non-NLP core is measured fairly when NLP is not installed.
    det_tp = det_fn = 0
    for sc in SCENARIOS:
        if sc.needs_nlp and not pipe.nlp_available:
            continue
        found, expected = _run_scenario(sc, pipe)
        det_tp += len(found & expected)
        det_fn += len(expected - found)
    det_recall = det_tp / (det_tp + det_fn) if (det_tp + det_fn) else 1.0

    return {
        "nlp_available": pipe.nlp_available,
        "totals": {"tp": tp, "fp": fp, "fn": fn,
                   "precision": round(precision, 3), "recall": round(recall, 3),
                   "f1": round(f1, 3)},
        "recall_excluding_nlp_scenarios": round(det_recall, 3),
        "per_type": per_type,
        "scenarios": rows,
    }


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2))
    tot = result["totals"]
    print(f"\nRecall={tot['recall']:.2%} Precision={tot['precision']:.2%} F1={tot['f1']:.2%}")
    print(f"NLP available: {result['nlp_available']}")
    if tot["recall"] < 0.95:
        print("NOTE: recall below the 0.95 synthetic target. See report for failure analysis.")
