"""In-memory project store for the prototype (documented path to SQLite/Postgres).

Keeps projects, uploaded datasets, findings, and policies in memory. Vaults are
on disk (encrypted) and keyed per project. This is intentionally simple for the
MVP; design.md records the migration path.
"""
from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from typing import Optional

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
    def __init__(self, vault_dir: Optional[str] = None) -> None:
        self.projects: dict[str, Project] = {}
        self.vault_dir = vault_dir or os.environ.get(
            "PRIVACYFORGE_VAULT_DIR", os.path.join(os.getcwd(), "vault")
        )

    def create_project(self, name: str) -> Project:
        pid = "proj_" + secrets.token_hex(6)
        p = Project(project_id=pid, name=name)
        self.projects[pid] = p
        return p

    def get(self, project_id: str) -> Optional[Project]:
        return self.projects.get(project_id)
