import pytest

from privacyforge.detection import DetectionPipeline
from privacyforge.engine import apply_to_dataset
from privacyforge.ingestion import parse_csv
from privacyforge.models import Category, Finding, Dataset, ColumnSchema
from privacyforge.policy import Policy, PolicyRule
from privacyforge.transform import Transformer
from privacyforge.vault import TokenVault
from privacyforge.verification import build_risk_report, export_gate, k_anonymity


@pytest.fixture(autouse=True)
def _master_key(monkeypatch):
    monkeypatch.setenv("PRIVACYFORGE_MASTER_KEY", "test-master-key")


def _dataset():
    data = b"student_id,name,gpa\nSTU-0001,Jane Doe,3.5\nSTU-0002,Bob Lee,3.9\nSTU-0001,Jane Doe,3.5\n"
    return parse_csv(data)


def test_tokenize_preserves_join(tmp_path):
    ds = _dataset()
    pipe = DetectionPipeline(use_nlp=False)
    findings = pipe.detect_dataset(ds)
    policy = Policy(
        rules=[
            PolicyRule(match_type="column", match_value="student_id", operator="tokenize"),
            PolicyRule(match_type="column", match_value="gpa", operator="retain"),
        ],
        default_operator="retain",
    )
    v = TokenVault("p1", tmp_path)
    t = Transformer(vault=v)
    res = apply_to_dataset(ds, findings, policy, t)
    sids = [r["student_id"] for r in res.dataset.rows]
    # Same original id -> same token (join preserved), different ids differ.
    assert sids[0] == sids[2]
    assert sids[0] != sids[1]
    # GPA retained unchanged.
    assert [r["gpa"] for r in res.dataset.rows] == ["3.5", "3.9", "3.5"]


def test_residual_scan_catches_leak():
    # An email left in the output must be caught by the second pass.
    ds = Dataset(
        columns=[ColumnSchema(name="notes", dtype="string")],
        rows=[{"notes": "reach me at leak@example.edu"}],
        kind="csv",
    )
    report = build_risk_report(ds, operators_used={})
    assert any(f.entity_type == "EMAIL" for f in report.residual_findings)


def test_export_gate_blocks_on_residual_pii():
    ds = Dataset(
        columns=[ColumnSchema(name="notes", dtype="string")],
        rows=[{"notes": "ssn 123-45-6789"}],
        kind="csv",
    )
    report = build_risk_report(ds, operators_used={})
    gate = export_gate(report, processing_ok=True)
    assert not gate.allow_export and gate.reasons


def test_export_gate_blocks_on_failure():
    ds = Dataset(columns=[ColumnSchema(name="x")], rows=[{"x": "ok"}], kind="csv")
    report = build_risk_report(ds, operators_used={})
    gate = export_gate(report, processing_ok=False)
    assert not gate.allow_export


def test_k_anonymity_detects_unique():
    ds = Dataset(
        columns=[ColumnSchema(name="zip"), ColumnSchema(name="age")],
        rows=[{"zip": "021", "age": "19"}, {"zip": "900", "age": "55"}],
        kind="csv",
    )
    ka = k_anonymity(ds, ["zip", "age"])
    assert ka["k"] == 1 and ka["unique_records"] == 2


def test_no_perfect_safe_claim():
    ds = Dataset(columns=[ColumnSchema(name="x")], rows=[{"x": "ok"}], kind="csv")
    report = build_risk_report(ds, operators_used={})
    blob = report.model_dump_json()
    assert "100%" not in blob and "fully anonymized" not in blob.lower()
