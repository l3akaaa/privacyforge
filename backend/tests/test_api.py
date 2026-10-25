import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("PRIVACYFORGE_MASTER_KEY", "test-master-key")
    monkeypatch.setenv("PRIVACYFORGE_VAULT_DIR", str(tmp_path / "vault"))
    monkeypatch.setenv("PRIVACYFORGE_STATE_DIR", str(tmp_path / "state"))
    import importlib
    import privacyforge.api as api
    importlib.reload(api)
    return TestClient(api.app)


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_presets_have_disclaimer(client):
    r = client.get("/api/v1/presets")
    assert r.status_code == 200
    for _, policy in r.json().items():
        assert "not a legal-compliance certification" in policy["disclaimer"]


def test_full_api_flow(client):
    pid = client.post("/api/v1/projects", json={"name": "demo"}).json()["project_id"]
    csv = b"student_id,name,email,gpa\nSTU-0001,Jane Doe,jane@u.edu,3.5\nSTU-0001,Jane Doe,jane@u.edu,3.5\n"
    up = client.post(f"/api/v1/projects/{pid}/files",
                     files={"file": ("d.csv", csv, "text/csv")})
    assert up.status_code == 200
    fid = up.json()["file_id"]

    det = client.post(f"/api/v1/projects/{pid}/detect", json={"file_id": fid})
    assert det.status_code == 200
    assert det.json()["summary"]["total"] > 0

    client.put(f"/api/v1/projects/{pid}/policy", json={"preset_name": "student_records"})
    tr = client.post(f"/api/v1/projects/{pid}/transform", json={"file_id": fid})
    assert tr.status_code == 200
    assert tr.json()["change_count"] > 0

    ver = client.post(f"/api/v1/projects/{pid}/verify",
                      json={"file_id": fid, "quasi_identifiers": []})
    assert ver.status_code == 200
    assert "risk_report" in ver.json()


def test_rule_dry_run(client):
    pid = client.post("/api/v1/projects", json={"name": "r"}).json()["project_id"]
    r = client.post(f"/api/v1/projects/{pid}/custom-rules/test", json={
        "rule": {"id": "x", "entity_type": "BADGE", "pattern": r"BDG-\d{4}"},
        "sample": "see BDG-1234 here",
    })
    assert r.status_code == 200
    assert len(r.json()["matches"]) == 1


def test_detokenize_requires_auth(client):
    pid = client.post("/api/v1/projects", json={"name": "a"}).json()["project_id"]
    csv = b"student_id\nSTU-9\n"
    fid = client.post(f"/api/v1/projects/{pid}/files",
                      files={"file": ("d.csv", csv, "text/csv")}).json()["file_id"]
    client.post(f"/api/v1/projects/{pid}/detect", json={"file_id": fid})
    client.put(f"/api/v1/projects/{pid}/policy",
               json={"policy": {"name": "c", "rules": [
                   {"match_type": "column", "match_value": "student_id", "operator": "tokenize"}],
                   "default_operator": "retain"}})
    tr = client.post(f"/api/v1/projects/{pid}/transform", json={"file_id": fid})
    token = tr.json()["preview_after"][0]["student_id"]
    bad = client.post(f"/api/v1/projects/{pid}/detokenize",
                      json={"tokens": [token], "authorization": "wrong"})
    assert bad.status_code == 403


def test_get_project_404_when_missing(client):
    r = client.get("/api/v1/projects/proj_does_not_exist")
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "not_found"


def test_project_survives_store_reload(client, tmp_path):
    # Create a project and upload a file.
    pid = client.post("/api/v1/projects", json={"name": "persist me"}).json()["project_id"]
    csv = b"student_id,email\nSTU-1,a@u.edu\n"
    up = client.post(f"/api/v1/projects/{pid}/files",
                     files={"file": ("d.csv", csv, "text/csv")})
    fid = up.json()["file_id"]

    # Simulate a backend restart: build a fresh Store against the same state dir.
    from privacyforge.store import Store
    reloaded = Store(vault_dir=str(tmp_path / "vault"), state_dir=str(tmp_path / "state"))
    proj = reloaded.get(pid)
    assert proj is not None
    assert proj.name == "persist me"
    assert fid in proj.files
    assert proj.files[fid].dataset is not None
