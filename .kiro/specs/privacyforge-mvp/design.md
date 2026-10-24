# PrivacyForge -- Technical Design (Phase 1 MVP)

## 1. System overview

```
+-------------------+        HTTP/JSON (/api/v1)        +---------------------------+
|  Next.js frontend | <-------------------------------> |  FastAPI backend          |
|  (TypeScript,     |                                   |  (Python 3.12)            |
|   Tailwind)       |                                   |                           |
+-------------------+                                   |  detection pipeline       |
                                                        |  policy + transform       |
                                                        |  token vault (encrypted)  |
                                                        |  verification + utility   |
                                                        |  export + reporting       |
                                                        +------------+--------------+
                                                                     |
                                                        +------------v--------------+
                                                        | SQLite (app data)         |
                                                        | Encrypted vault file(s)   |
                                                        | Controlled temp dir       |
                                                        +---------------------------+
```

All detection and transformation happen in the backend. The frontend only
uploads, displays, collects policy choices/corrections, and downloads results.

## 2. Backend modules & interfaces

Each detector implements a common `Detector` protocol so any one can be swapped:

```python
class Finding(BaseModel):
    entity_type: str          # EMAIL, PERSON, STUDENT_ID, ...
    category: Literal["pii", "sensitive", "quasi"]
    start: int | None         # char span (text) or None for whole-cell
    end: int | None
    field: str | None         # column name for structured data
    row: int | None           # row index for structured data
    value_preview: str        # masked preview, never full raw value in logs
    score: float | None       # raw detector score, 0..1, uncalibrated
    source: str               # "regex:email", "presidio:PERSON", "spacy", "column", "custom:<id>"
    context: str | None       # surrounding snippet for NLP findings
    review_needed: bool

class Detector(Protocol):
    name: str
    def detect_text(self, text: str, field: str | None, row: int | None) -> list[Finding]: ...
    def detect_column(self, column: str, values: list[str]) -> list[Finding]: ...
```

- **ingestion**: `parse(file) -> Dataset` (typed table: columns, rows, dtypes) or
  `TextDoc`. Validates type by content sniff, enforces limits, rejects unsafe XLSX.
- **detection**: runs Layer A (regex+validators+Presidio pattern recognizers),
  Layer B (spaCy+Presidio NLP), Layer C (column/dtype/cardinality/format heuristics),
  Layer D (classifier mapping entity->category + user overrides), Layer E
  (user custom rules). Each returns `Finding`s.
- **aggregation**: span-overlap merge, conflict resolution (priority:
  deterministic > custom > NLP > column-heuristic for label; keep all sources),
  emits deduped `Finding`s with review flags.
- **policy**: `Policy` = ordered rules {match: entity_type|column|category,
  operator, params}. `resolve(finding) -> Operator`. Presets are stored Policy JSON.
- **transform**: operators below. Pure functions over value + params + vault.
- **vault**: see section 5.
- **verification**: rescan output through detection; uniqueness + optional
  k-anonymity over selected quasi-identifiers; leakage scan (cells, metadata,
  hidden content); builds `RiskReport`; computes fail-safe gate decision.
- **utility**: before/after `QualityReport`.
- **export**: writes transformed file + audit report iff gate passes.

## 3. Transformation operators

| Operator   | Behavior                                                        | Reversible |
|------------|-----------------------------------------------------------------|------------|
| redact     | replace with `[REDACTED_<TYPE>]`                                | no         |
| mask       | keep policy-defined visible chars, replace rest with `*`        | no         |
| tokenize   | replace with vault token `TOK_<base32>`; consistent per project | yes (vault)|
| synthetic  | Faker value, consistent per project via seeded map              | no*        |
| generalize | bucket: age->range, date->month/year, zip->prefix               | no         |
| retain     | leave unchanged (explicit, recorded)                            | n/a        |

\* synthetic is not reversible but is a mapping; it is pseudonymization in effect
and is labeled as such, never "anonymous".

## 4. API contracts (/api/v1)

```
POST /projects                      -> {project_id}
POST /projects/{id}/files           (multipart) -> {file_id, schema, preview}
POST /projects/{id}/detect          {file_id} -> {findings: Finding[], summary}
PATCH /projects/{id}/findings       {add:[...], remove:[ids], reclassify:[...]} -> {findings}
GET  /projects/{id}/policy          -> {policy}
PUT  /projects/{id}/policy          {policy | preset_name} -> {policy}
POST /projects/{id}/custom-rules/test {rule, sample} -> {matches}
POST /projects/{id}/transform       {file_id} -> {preview: before/after rows, change_count}
POST /projects/{id}/verify          {file_id} -> {risk_report, quality_report, gate: pass|block, reasons}
POST /projects/{id}/export          {file_id, override?} -> file download | 409 gate-blocked
POST /projects/{id}/detokenize      {tokens, authorization} -> {values} (authorized only)
DELETE /projects/{id}/vault         -> {deleted}
```

All bodies are Pydantic models. Errors return `{error_code, message}` with no raw
data or stack traces.

## 5. Token vault design

- Per-project vault file: `vault/<project_id>.vault`, AES-GCM (via `cryptography`
  Fernet or AESGCM) encrypted JSON `{original_hash -> token, token -> enc(original)}`.
- Key derivation: project key derived from a master key (env var
  `PRIVACYFORGE_MASTER_KEY`, never in repo) + per-project salt via HKDF. No hardcoded
  keys. If master key absent, vault operations refuse rather than use a default.
- Token format: `TOK_` + base32 of `secrets.token_bytes(10)` -> ~16 chars, checked
  for collision within project.
- Lookup is by HMAC(original) so the plaintext original is never stored as a map key.
- Detokenize requires the caller to present the project authorization secret; the
  endpoint verifies it before decrypting.
- Isolation: keys are per-project; project A's key cannot decrypt project B's vault.
- Nothing from the vault is ever logged.

## 6. Dataset-aware detection (Layer C) detail

Signals combined into a column-level likelihood (reported as a qualitative band):
- Column name match against a configurable dictionary (`*_id`, `student_number`,
  `account_number`, `email`, `dob`, ...).
- Uniqueness ratio (distinct/count) -> high cardinality suggests identifier.
- Consistent format/prefix across values (e.g. regex of the modal shape).
- Dtype (free-text object columns get NLP; numeric high-cardinality flagged for review).
Never auto-assume every unique value is PII: uncertain columns are flagged
`review_needed=True`, not silently transformed.

## 7. Data models (SQLite)

- `projects(id, name, created_at, policy_json, settings_json)`
- `files(id, project_id, filename, kind, schema_json, created_at)`
- `findings(id, project_id, file_id, json)`  (findings snapshot, user-editable)
- `runs(id, project_id, file_id, risk_report_json, quality_report_json, gate, created_at)`
- Vault is NOT in SQLite; it is separate encrypted files.

## 8. Threat model (STRIDE-lite)

| Threat                              | Mitigation                                           |
|-------------------------------------|------------------------------------------------------|
| Prompt injection via file content   | File text treated as data; never fed as instructions |
| Original values leak via logs       | Log filter; previews masked; vault never logged       |
| Cross-project token access          | Per-project keys + isolation tests                   |
| Key exposure                        | No hardcoded keys; env/keystore; refuse if absent     |
| Decompression / XML bomb            | Size+ratio limits; safe parsers; reject on exceed     |
| Malicious XLSX (formulas/macros)    | Value-only extraction or rejection; recorded in report|
| Residual PII in "clean" output      | Mandatory second-pass rescan + fail-safe gate         |
| Over-claiming safety                | No "100% safe"; limitations in every report           |
| Unauthorized detokenization         | Authorization secret required                        |

## 9. Technology decisions & trade-offs

- **Presidio** (MIT) for recognizers + anonymizer scaffolding: mature, extensible,
  context enhancement. Trade-off: English-centric defaults; Layer C/E compensate.
- **spaCy** `en_core_web_lg` (MIT) for NER: good names/orgs/locations without a GPU.
  Trade-off: statistical, misses novel formats -> combined with deterministic layers.
- **Faker** (MIT) for synthetic values. Trade-off: realistic output must be guarded
  against generating valid credentials.
- **FastAPI + Pydantic** (MIT): typed, async, auto OpenAPI.
- **cryptography** library for AES-GCM/Fernet: never roll our own crypto.
- **SQLite** now, documented migration to PostgreSQL later.
- **Next.js/TS/Tailwind** for an accessible, modern UI.

## 10. Phase boundaries
Phase 1 = text/CSV/XLSX/JSON + full detect/transform/verify/export + tests.
PDF/DOCX/OCR/metadata sanitization = Phase 2. Multilingual, batch, RBAC, DB
connectors, advanced re-identification = Phase 3. See roadmap.md.
