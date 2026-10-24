# PrivacyForge -- Implementation Tasks (Phase 1 MVP)

Status: [ ] todo  [~] in progress  [x] done  [>] deferred to later phase
Each task lists the requirement(s) it satisfies. Order respects dependencies.

## Milestone 0 -- Repo & environment (GitHub-ready)
- [x] M0.1 Repo skeleton: `/backend`, `/data`, `/docs`, README, LICENSE, `.gitignore`.  (R9.1)
- [x] M0.2 Backend env: requirements files, ruff, pytest.  (standards)
- [ ] M0.3 Frontend env: Next.js + TS + Tailwind scaffold.  (R7)  -- PLANNED
- [ ] M0.4 CI config (lint + test) and CONTRIBUTING note.  (standards)

## Milestone 1 -- Ingestion (foundation)
- [x] M1.1 Typed Dataset/TextDoc models.  (R1.1)
- [x] M1.2 CSV/JSON/TXT parsers.  (R1.1)
- [x] M1.3 XLSX parser with formula/hidden/macro detection + value-only safe mode.  (R1.4)
- [x] M1.4 Content-sniff type validation; size limit; bomb guards.  (R1.2, R1.3, R1.5)
- [x] M1.5 Tests: valid files parse; unsafe/corrupt/oversized rejected.  (R1.*)

## Milestone 2 -- Detection pipeline (core)
- [x] M2.1 Detector protocol + Finding model.  (design 2)
- [x] M2.2 Layer A deterministic (+ Luhn/SSN validators).  (R2.1)
- [x] M2.3 Layer B NLP: spaCy + Presidio (optional install), context capture.  (R2.2)
- [x] M2.4 Layer C dataset-aware: column name dict, cardinality, format/prefix.  (R2.3)
- [x] M2.5 Layer D contextual classification (pii/sensitive/quasi) + override.  (R2.4, R2.5)
- [x] M2.6 Layer E custom rules + dry-run.  (R2.6)
- [x] M2.7 Aggregation: overlap merge, conflict resolve, review flags.  (R2.7, R2.8)
- [x] M2.8 Tests per layer + aggregation; benchmark harness.  (R2.*)

## Milestone 3 -- Token vault (security-critical)
- [x] M3.1 Key provisioning (master key env + HKDF salt), refuse if absent.  (R4.3)
- [x] M3.2 AES-GCM vault store, HMAC-keyed lookups, no plaintext keys.  (R4.3)
- [x] M3.3 Secure token generation (`secrets`), collision check.  (R4.1)
- [x] M3.4 Consistent-per-project, isolated-across-project mapping.  (R4.2)
- [x] M3.5 Authorized detokenize; delete/retention.  (R4.4, R4.5)
- [x] M3.6 Tests: isolation, no-plaintext-on-disk, no-secrets-in-logs, auth.  (R4.*)

## Milestone 4 -- Policy & transform
- [x] M4.1 Policy model + resolve; 5 presets with disclaimers.  (R3.2, R3.3)
- [x] M4.2 Operators: redact, mask, tokenize, synthetic, generalize, retain.  (R3.1)
- [x] M4.3 Project-consistent synthetic; guard against valid credentials/cards.  (R3.4)
- [x] M4.4 Tests per operator; policy resolution; preset loading.  (R3.*)

## Milestone 5 -- Verification & utility
- [x] M5.1 Second-pass residual rescan over output.  (R5.1)
- [x] M5.2 Uniqueness + optional k-anonymity over selected quasi-identifiers.  (R5.2)
- [x] M5.3 Leakage checks (cells + extensible metadata hooks).  (R5.3)
- [x] M5.4 Risk report (all sections, no "100% safe").  (R5.4)
- [x] M5.5 Fail-safe export gate + documented authorized override.  (R5.5)
- [x] M5.6 Utility comparison report.  (R6.2)
- [x] M5.7 Tests: planted residual caught; gate blocks; join preserved.  (R5.*, R6.1)

## Milestone 6 -- API layer
- [x] M6.1 FastAPI app, versioned routes, Pydantic models, safe error mapping.  (design 4, R8)
- [x] M6.2 Endpoints: projects/files/detect/findings/policy/transform/verify/export/detokenize.  (design 4)
- [x] M6.3 Masked previews; vault-dir config; size limits at the edge.  (R8)
- [x] M6.4 API integration tests.  (standards)

## Milestone 7 -- Frontend  (Implemented, wired to live API; build passes)
- [x] M7.1 Dashboard + Upload Workspace.  (R7.1)
- [x] M7.2 Detection Review (highlights, categories, explanations, keep/remove).  (R7.2)
- [x] M7.3 Policy Editor (per entity/column, presets + disclaimer).  (R3.3, R7.1)
- [x] M7.4 Before/After Preview.  (R7.1)
- [x] M7.5 Verification Report + Export pages.  (R7.1)
- [x] M7.6 Accessibility pass (skip link, labels, focus rings, confidence bands).  (R7.3)

## Milestone 8 -- Benchmark, data, docs
- [x] M8.1 Synthetic university dataset (data/sample_university.csv).  (R9.1)
- [x] M8.2 Benchmark suite: scenarios, precision/recall/F1, FP/FN counts.  (Sec13)
- [x] M8.3 Benchmark report (actual numbers; no fabrication).  (Sec13)
- [x] M8.4 End-to-end test of the flagship university workflow.  (Sec14)
- [x] M8.5 SECURITY-LIMITATIONS.md, setup/run instructions, ROADMAP.md.  (R9.1)

## Test matrix (16 required scenarios -> tasks)
1 email/phone -> M2.2/M2.8 | 2 names in sentences -> M2.3/M2.8 |
3 org student IDs -> M2.4/M2.8 | 4 odd sensitive columns -> M2.4 |
5 repeated identities -> M3.4/M4.3 | 6 cross-file identity -> M3.4/R6.1 |
7 ids w/o labels -> M2.2/M2.4 | 8 benign look-alikes -> M2.2 (validators) |
9 mixed PII+business -> M2.5 | 10 ambiguous names/places -> M2.3/M2.7 |
11 false-positive correction -> M2.7/M7.2 | 12 token consistency -> M3.4 |
13 token separation -> M3.6 | 14 residual values -> M5.1 |
15 unsupported/failed -> M1.5/M5.5 | 16 corrupted/malicious -> M1.4/M1.5

## Review gates
- Before Milestone 3 (vault) and the security-critical parts of Milestone 5/6,
  present design for user review (per the brief). Do not build the crypto/vault
  until that review is acknowledged.
