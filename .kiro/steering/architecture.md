# PrivacyForge -- Architecture Principles

## Shape
Modular full-stack app. Backend is the source of truth for all processing; the
frontend never performs detection or transformation itself.

- Frontend: Next.js + TypeScript + Tailwind CSS, accessible components.
- Backend: Python + FastAPI. Presidio Analyzer/Anonymizer, spaCy, Faker,
  pandas/openpyxl for structured data.
- Storage: SQLite for the local prototype, with a documented path to PostgreSQL.
  Encrypted token vault kept logically separate from application data.

## Backend module boundaries (each replaceable in isolation)
1. ingestion    -- file upload, type validation, safe parsing, resource limits.
2. detection    -- the multi-layer pipeline (A deterministic, B NLP, C
                   dataset-aware, D contextual classification, E custom rules).
3. aggregation  -- merge/deduplicate detections, resolve conflicts, keep source,
                   span, score, context, review-needed flag.
4. policy       -- entity/column -> operator mapping; presets; validation.
5. transform    -- redact, mask, tokenize, synthetic, generalize, retain.
6. vault        -- cryptographically secure tokenization + encrypted mapping store.
7. verification -- residual-PII rescan, quasi-identifier/k-anonymity, leakage
                   checks, risk report, fail-safe export gate.
8. utility      -- before/after data-quality comparison.
9. export       -- build output files + audit report, enforce fail-safe gate.

## Rules
- A detector is a plugin behind a common interface. Adding or swapping one
  (regex, Presidio recognizer, spaCy model, future ML model) must not require
  touching aggregation or transform.
- Versioned API (/api/v1/...). Typed request/response models (Pydantic).
- Deterministic core logic is unit-testable without the web layer.
- No global mutable state for per-project token maps; scope everything by project.
- Evaluate dependency licenses before adoption (Presidio MIT, spaCy MIT,
  Faker MIT, FastAPI MIT -- all permissive; record any that are not).

## Data flow (happy path)
upload -> ingestion (validate+parse) -> detection (A-E in parallel per field) ->
aggregation -> [user review/correct] -> policy resolve -> transform (+vault) ->
verification (rescan+risk) -> fail-safe gate -> export (data + report).
