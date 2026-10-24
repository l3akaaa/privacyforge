# PrivacyForge — Roadmap

Honest status. Implemented = working + tested. Partial = scaffolded. Planned = not started.

## Phase 1 — Functional MVP

| Area | Status |
|------|--------|
| Ingestion: TXT/CSV/JSON/XLSX + safety guards | Implemented |
| Detection A (deterministic + validators) | Implemented |
| Detection B (Presidio + spaCy NLP) | Implemented as optional install |
| Detection C (dataset-aware) | Implemented |
| Detection D (PII/sensitive/quasi classification) | Implemented |
| Detection E (custom no-code rules + dry-run) | Implemented |
| Detection F (aggregation) | Implemented |
| Policy engine + 5 presets | Implemented |
| Transform (redact/mask/tokenize/synthetic/generalize/retain) | Implemented |
| Secure token vault (AES-GCM, HKDF, isolation, auth) | Implemented |
| Verification (residual scan, k-anonymity, leakage, risk report, fail-safe gate) | Implemented |
| Utility comparison report | Implemented |
| FastAPI backend (versioned, typed) | Implemented |
| Automated tests (unit + API + e2e + benchmark) | Implemented (43 tests) |
| Synthetic university dataset | Implemented |
| **Next.js frontend (7 pages)** | **Planned — API contracts ready** |

## Phase 2 — Expanded document support (planned)

- DOCX and text-based PDF ingestion.
- Scanned PDF / image OCR.
- Metadata inspection and sanitization.
- Safe PDF handling: never black-box redaction; if underlying text/objects/
  metadata cannot be trustworthily removed, export sanitized extracted text.

## Phase 3 — Advanced (planned)

- Multilingual detection; additional optional local models.
- Batch processing.
- Role-based team collaboration with real auth.
- Advanced re-identification risk analysis.
- Enterprise database connectors.
- PostgreSQL storage (migration path documented in design.md).
- Deployment options for institutions.

## Next concrete step

Build the Next.js frontend against the existing API:
Dashboard → Upload → Detection Review → Policy Editor → Before/After →
Verification Report → Export. The backend endpoints and typed responses already
exist (`backend/privacyforge/api.py`).
