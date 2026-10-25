"""FastAPI application (Milestone 6; design section 4).

Versioned endpoints, typed Pydantic bodies, safe error mapping (no raw data or
stack traces leak to the client). All processing is delegated to the backend
modules; the API only orchestrates.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import __version__
from .detection import CustomRule, DetectionPipeline, dry_run_rule
from .engine import apply_to_dataset, apply_to_text
from .errors import PrivacyForgeError
from .ingestion import parse_upload
from .models import Dataset
from .policy import PRESETS, Policy, get_preset
from .store import Store
from .transform import Transformer
from .utility import compare
from .vault import TokenVault
from .verification import build_risk_report, export_gate

app = FastAPI(title="PrivacyForge API", version=__version__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
store = Store()


def _err(exc: PrivacyForgeError, status: int = 400) -> HTTPException:
    return HTTPException(status_code=status, detail={"error_code": exc.code, "message": exc.message})


# ---- request/response models -------------------------------------------

class CreateProject(BaseModel):
    name: str = "Untitled project"


class PolicyBody(BaseModel):
    policy: Optional[Policy] = None
    preset_name: Optional[str] = None


class RuleTestBody(BaseModel):
    rule: CustomRule
    sample: str


class VerifyBody(BaseModel):
    file_id: str
    quasi_identifiers: list[str] = []


class ExportBody(BaseModel):
    file_id: str
    override: bool = False


class DetokenizeBody(BaseModel):
    tokens: list[str]
    authorization: str


# ---- endpoints ----------------------------------------------------------

@app.get("/api/v1/health")
def health() -> dict[str, Any]:
    pipe = DetectionPipeline()
    return {"status": "ok", "version": __version__, "nlp_available": pipe.nlp_available}


@app.get("/api/v1/presets")
def list_presets() -> dict[str, Any]:
    return {name: get_preset(name).model_dump() for name in PRESETS}


@app.post("/api/v1/projects")
def create_project(body: CreateProject) -> dict[str, str]:
    p = store.create_project(body.name)
    return {"project_id": p.project_id, "name": p.name}


@app.get("/api/v1/projects/{project_id}")
def get_project(project_id: str) -> dict[str, Any]:
    proj = store.get(project_id)
    if not proj:
        raise HTTPException(404, detail={"error_code": "not_found", "message": "Project not found."})
    files = [
        {"file_id": fe.file_id, "filename": fe.filename}
        for fe in proj.files.values()
    ]
    return {"project_id": proj.project_id, "name": proj.name, "files": files}


@app.post("/api/v1/projects/{project_id}/files")
async def upload_file(project_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
    proj = store.get(project_id)
    if not proj:
        raise HTTPException(404, detail={"error_code": "not_found", "message": "Project not found."})
    data = await file.read()
    try:
        parsed, warnings = parse_upload(file.filename or "upload", data)
    except PrivacyForgeError as exc:
        raise _err(exc)
    import secrets as _s
    fid = "file_" + _s.token_hex(6)
    from .store import FileEntry
    entry = FileEntry(file_id=fid, filename=file.filename or "upload", warnings=warnings)
    schema: dict[str, Any]
    if isinstance(parsed, Dataset):
        entry.dataset = parsed
        schema = {"kind": parsed.kind, "columns": [c.model_dump() for c in parsed.columns],
                  "row_count": len(parsed.rows)}
        preview = parsed.rows[:10]
    else:
        entry.textdoc = parsed
        schema = {"kind": "txt", "length": len(parsed.text)}
        preview = parsed.text[:500]
    proj.files[fid] = entry
    store.save()
    return {"file_id": fid, "schema": schema, "preview": preview, "warnings": warnings}


def _pipeline(proj) -> DetectionPipeline:
    rules = getattr(proj, "_custom_rules", [])
    return DetectionPipeline(custom_rules=rules)


@app.post("/api/v1/projects/{project_id}/detect")
def detect(project_id: str, body: dict) -> dict[str, Any]:
    proj = store.get(project_id)
    if not proj:
        raise HTTPException(404, detail={"error_code": "not_found", "message": "Project not found."})
    entry = proj.files.get(body.get("file_id", ""))
    if not entry:
        raise HTTPException(404, detail={"error_code": "not_found", "message": "File not found."})
    pipe = _pipeline(proj)
    if entry.dataset is not None:
        findings = pipe.detect_dataset(entry.dataset)
    else:
        findings = pipe.detect_text(entry.textdoc)  # type: ignore[arg-type]
    proj.findings[entry.file_id] = findings
    store.save()
    by_cat: dict[str, int] = {}
    for f in findings:
        by_cat[f.category.value] = by_cat.get(f.category.value, 0) + 1
    return {
        "findings": [f.model_dump() for f in findings],
        "summary": {"total": len(findings), "by_category": by_cat,
                    "review_needed": sum(1 for f in findings if f.review_needed)},
        "nlp_available": pipe.nlp_available,
    }


@app.post("/api/v1/projects/{project_id}/custom-rules/test")
def test_custom_rule(project_id: str, body: RuleTestBody) -> dict[str, Any]:
    return {"matches": dry_run_rule(body.rule, body.sample)}


@app.put("/api/v1/projects/{project_id}/policy")
def set_policy(project_id: str, body: PolicyBody) -> dict[str, Any]:
    proj = store.get(project_id)
    if not proj:
        raise HTTPException(404, detail={"error_code": "not_found", "message": "Project not found."})
    if body.preset_name:
        preset = get_preset(body.preset_name)
        if not preset:
            raise HTTPException(400, detail={"error_code": "bad_preset", "message": "Unknown preset."})
        proj.policy = preset
    elif body.policy:
        proj.policy = body.policy
    store.save()
    return {"policy": proj.policy.model_dump()}


@app.get("/api/v1/projects/{project_id}/policy")
def get_policy(project_id: str) -> dict[str, Any]:
    proj = store.get(project_id)
    if not proj:
        raise HTTPException(404, detail={"error_code": "not_found", "message": "Project not found."})
    return {"policy": proj.policy.model_dump()}


def _vault(project_id: str, *, autosave: bool = True) -> TokenVault:
    return TokenVault(project_id, store.vault_dir, autosave=autosave)


@app.post("/api/v1/projects/{project_id}/transform")
def transform(project_id: str, body: dict) -> dict[str, Any]:
    proj = store.get(project_id)
    if not proj:
        raise HTTPException(404, detail={"error_code": "not_found", "message": "Project not found."})
    entry = proj.files.get(body.get("file_id", ""))
    if not entry:
        raise HTTPException(404, detail={"error_code": "not_found", "message": "File not found."})
    findings = proj.findings.get(entry.file_id, [])
    try:
        vault = _vault(project_id, autosave=False)
        t = Transformer(vault=vault, project_seed=project_id)
        if entry.dataset is not None:
            res = apply_to_dataset(entry.dataset, findings, proj.policy, t)
            entry_after = res.dataset
            preview_before = entry.dataset.rows[:10]
            preview_after = res.dataset.rows[:10]
        else:
            res = apply_to_text(entry.textdoc, findings, proj.policy, t)  # type: ignore[arg-type]
            entry_after = res.textdoc
            preview_before = entry.textdoc.text[:500]  # type: ignore[union-attr]
            preview_after = res.textdoc.text[:500]  # type: ignore[union-attr]
        vault.flush()
    except PrivacyForgeError as exc:
        raise _err(exc)
    proj.__dict__["_last_transform"] = (entry.file_id, entry_after, res)
    return {
        "change_count": res.change_count,
        "operators_used": res.operators_used,
        "preview_before": preview_before,
        "preview_after": preview_after,
    }


@app.post("/api/v1/projects/{project_id}/verify")
def verify(project_id: str, body: VerifyBody) -> dict[str, Any]:
    proj = store.get(project_id)
    if not proj:
        raise HTTPException(404, detail={"error_code": "not_found", "message": "Project not found."})
    last = proj.__dict__.get("_last_transform")
    if not last or last[0] != body.file_id:
        raise HTTPException(400, detail={"error_code": "no_transform",
                                         "message": "Run transform before verify."})
    _, output, res = last
    report = build_risk_report(output, res.operators_used, body.quasi_identifiers)
    gate = export_gate(report, processing_ok=True)
    quality = None
    entry = proj.files.get(body.file_id)
    if entry and entry.dataset is not None and isinstance(output, Dataset):
        quality = compare(entry.dataset, output,
                          [c for _, c in res.changed_cells]).model_dump()
    return {
        "risk_report": report.model_dump(),
        "quality_report": quality,
        "gate": "pass" if gate.allow_export else "block",
        "reasons": gate.reasons,
    }


@app.post("/api/v1/projects/{project_id}/export")
def export(project_id: str, body: ExportBody) -> dict[str, Any]:
    proj = store.get(project_id)
    if not proj:
        raise HTTPException(404, detail={"error_code": "not_found", "message": "Project not found."})
    last = proj.__dict__.get("_last_transform")
    if not last or last[0] != body.file_id:
        raise HTTPException(400, detail={"error_code": "no_transform",
                                         "message": "Run transform before export."})
    _, output, res = last
    report = build_risk_report(output, res.operators_used)
    gate = export_gate(report, processing_ok=True)
    if not gate.allow_export and not body.override:
        raise HTTPException(409, detail={"error_code": "export_blocked",
                                         "message": "Export blocked by privacy gate.",
                                         "reasons": gate.reasons})
    if isinstance(output, Dataset):
        rows = output.rows
        payload = {"columns": output.column_names, "rows": rows}
    else:
        payload = {"text": output.text}
    return {"export": payload, "override_used": body.override and not gate.allow_export,
            "audit": {"operators_used": res.operators_used, "gate": gate.allow_export,
                      "gate_reasons": gate.reasons}}


@app.post("/api/v1/projects/{project_id}/detokenize")
def detokenize(project_id: str, body: DetokenizeBody) -> dict[str, Any]:
    try:
        vault = _vault(project_id)
        values = {tok: vault.detokenize(tok, body.authorization) for tok in body.tokens}
    except PrivacyForgeError as exc:
        raise _err(exc, status=403 if exc.code == "not_authorized" else 400)
    return {"values": values}


@app.delete("/api/v1/projects/{project_id}/vault")
def delete_vault(project_id: str) -> dict[str, Any]:
    try:
        _vault(project_id).delete()
    except PrivacyForgeError as exc:
        raise _err(exc)
    return {"deleted": True}
