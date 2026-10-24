"""End-to-end flagship workflow test (Section 14 definition of done).

Upload synthetic university data -> detect -> tokenize IDs consistently ->
redact names/emails -> preserve GPA -> residual rescan -> risk report -> export.
"""
import pytest

from privacyforge.detection import DetectionPipeline
from privacyforge.engine import apply_to_dataset
from privacyforge.ingestion import parse_csv
from privacyforge.policy import Policy, PolicyRule
from privacyforge.sample_data import generate_csv
from privacyforge.transform import Transformer
from privacyforge.vault import TokenVault
from privacyforge.verification import build_risk_report, export_gate


@pytest.fixture(autouse=True)
def _master_key(monkeypatch):
    monkeypatch.setenv("PRIVACYFORGE_MASTER_KEY", "test-master-key")


def test_flagship_university_workflow(tmp_path):
    # 1. Upload + parse.
    ds = parse_csv(generate_csv(n=40).encode("utf-8"))
    assert "student_id" in ds.column_names and "gpa" in ds.column_names

    # 2. Detect.
    pipe = DetectionPipeline(use_nlp=False)
    findings = pipe.detect_dataset(ds)
    types = {f.entity_type for f in findings}
    assert "EMAIL" in types               # direct identifier found
    assert any("ID" in t or "STUDENT" in t for t in types)  # university id found

    # 3. Policy: tokenize IDs, redact names/emails, preserve GPA.
    policy = Policy(
        rules=[
            PolicyRule(match_type="column", match_value="student_id", operator="tokenize"),
            PolicyRule(match_type="column", match_value="name", operator="redact"),
            PolicyRule(match_type="column", match_value="email", operator="redact"),
            PolicyRule(match_type="entity", match_value="EMAIL", operator="redact"),
            PolicyRule(match_type="column", match_value="gpa", operator="retain"),
        ],
        default_operator="retain",
    )

    # 4. Transform.
    vault = TokenVault("flagship", tmp_path)
    t = Transformer(vault=vault, project_seed="flagship")
    res = apply_to_dataset(ds, findings, policy, t)
    out = res.dataset

    # 5. Student IDs tokenized consistently (same id -> same token).
    id_map: dict[str, str] = {}
    for before, after in zip(ds.rows, out.rows):
        orig, tok = before["student_id"], after["student_id"]
        assert tok.startswith("TOK_")
        if orig in id_map:
            assert id_map[orig] == tok
        id_map[orig] = tok

    # 6. GPA preserved; names/emails changed.
    assert [r["gpa"] for r in out.rows] == [r["gpa"] for r in ds.rows]
    assert all(r["name"].startswith("[REDACTED") for r in out.rows)
    assert all("@university.edu" not in str(r["email"]) for r in out.rows)

    # 7. Residual scan + risk report. The entity-level EMAIL rule also catches
    #    emails embedded in free-text adviser_notes, so no value-level PII leaks.
    report = build_risk_report(out, res.operators_used, quasi_identifiers=["age", "zip"])
    assert "100%" not in report.model_dump_json()
    value_pii_left = [
        f for f in report.residual_findings
        if f.category.value == "pii" and (f.row is not None or f.start is not None)
    ]
    assert value_pii_left == []          # no real PII value remains in the output
    gate = export_gate(report, processing_ok=True)
    assert gate.allow_export             # fail-safe allows export once PII is handled

    # 8. Demonstrate the fail-safe BLOCKS when PII is left unhandled: a policy
    #    that retains everything must not pass the gate.
    leak_policy = Policy(rules=[], default_operator="retain")
    res_leak = apply_to_dataset(ds, pipe.detect_dataset(ds), leak_policy, t)
    report_leak = build_risk_report(res_leak.dataset, res_leak.operators_used)
    gate_leak = export_gate(report_leak, processing_ok=True)
    assert not gate_leak.allow_export    # original emails remain -> blocked
