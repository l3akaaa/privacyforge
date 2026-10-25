"""Project store for the prototype (documented path to SQLite/Postgres).

Keeps projects, uploaded datasets, findings, and policies. By default the
project list and uploaded files are persisted to disk as JSON so they survive
a backend restart (Requirement: a restart must not lose the user's project).
Vaults are on disk (encrypted) and keyed per project. This is intentionally
simple for the MVP; design.md records the migration path to a real database.
"""
from __future__ import annotations

import json
import os
import secrets
import tempfile
from dataclasses import dataclass, field
from typing import Any, Optional

from .models import Dataset, Finding, TextDoc
from .policy import Policy


@dataclass
class FileEntry:
    file_id: str
    filename: str
    dataset: Optional[Dataset] = None
    textdoc: Optional[TextDoc] = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class Project:
    project_id: str
    name: str
    files: dict[str, FileEntry] = field(default_factory=dict)
    findings: dict[str, list[Finding]] = field(default_factory=dict)  # by file_id
    policy: Policy = field(default_factory=Policy)


class Store:
    def __init__(self, vault_dir: Optional[str] = None, state_dir: Optional[str] = None) -> None:
        self.projects: dict[str, Project] = {}
        self.vault_dir = vault_dir or os.environ.get(
            "PRIVACYFORGE_VAULT_DIR", os.path.join(os.getcwd(), "vault")
        )
        # Where the persisted project list lives. Disable by setting
        # PRIVACYFORGE_PERSIST=0 (tests run in-memory).
        persist = os.environ.get("PRIVACYFORGE_PERSIST", "1") != "0"
        self.state_dir: Optional[str] = None
        if persist:
            self.state_dir = state_dir or os.environ.get(
                "PRIVACYFORGE_STATE_DIR", os.path.join(os.getcwd(), "state")
            )
            self._load()

    # -- persistence ------------------------------------------------------

    def _state_path(self) -> str:
        assert self.state_dir is not None
        return os.path.join(self.state_dir, "projects.json")

    def _save(self) -> None:
        """Write the whole project list to disk atomically. Best-effort:
        a disk error must never crash a request, so failures are swallowed."""
        if not self.state_dir:
            return
        try:
            os.makedirs(self.state_dir, exist_ok=True)
            data = {pid: self._project_to_dict(p) for pid, p in self.projects.items()}
            fd, tmp = tempfile.mkstemp(dir=self.state_dir, suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            os.replace(tmp, self._state_path())
        except OSError:
            pass

    def _load(self) -> None:
        if not self.state_dir:
            return
        path = self._state_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            return
        for pid, pd in data.items():
            try:
                self.projects[pid] = self._project_from_dict(pd)
            except Exception:
                # A single corrupt project must not block loading the rest.
                continue

    @staticmethod
    def _project_to_dict(p: "Project") -> dict[str, Any]:
        files: dict[str, Any] = {}
        for fid, fe in p.files.items():
            files[fid] = {
                "file_id": fe.file_id,
                "filename": fe.filename,
                "dataset": fe.dataset.model_dump() if fe.dataset is not None else None,
                "textdoc": fe.textdoc.model_dump() if fe.textdoc is not None else None,
                "warnings": fe.warnings,
            }
        return {
            "project_id": p.project_id,
            "name": p.name,
            "files": files,
            "findings": {fid: [f.model_dump() for f in fs] for fid, fs in p.findings.items()},
            "policy": p.policy.model_dump(),
        }

    @staticmethod
    def _project_from_dict(pd: dict[str, Any]) -> "Project":
        files: dict[str, FileEntry] = {}
        for fid, fe in (pd.get("files") or {}).items():
            files[fid] = FileEntry(
                file_id=fe["file_id"],
                filename=fe["filename"],
                dataset=Dataset(**fe["dataset"]) if fe.get("dataset") else None,
                textdoc=TextDoc(**fe["textdoc"]) if fe.get("textdoc") else None,
                warnings=fe.get("warnings", []),
            )
        findings = {
            fid: [Finding(**f) for f in fs]
            for fid, fs in (pd.get("findings") or {}).items()
        }
        policy = Policy(**pd["policy"]) if pd.get("policy") else Policy()
        return Project(
            project_id=pd["project_id"],
            name=pd["name"],
            files=files,
            findings=findings,
            policy=policy,
        )

    # -- CRUD -------------------------------------------------------------

    def create_project(self, name: str) -> Project:
        pid = "proj_" + secrets.token_hex(6)
        p = Project(project_id=pid, name=name)
        self.projects[pid] = p
        self._save()
        return p

    def get(self, project_id: str) -> Optional[Project]:
        return self.projects.get(project_id)

    def save(self) -> None:
        """Persist current project state. Callers invoke this after mutating
        a project (upload, detect, policy change) so the change survives a
        restart."""
        self._save()
