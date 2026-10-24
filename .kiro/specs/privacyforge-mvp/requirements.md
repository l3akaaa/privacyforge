# PrivacyForge -- Requirements Specification (Phase 1 MVP)

Status legend: [MVP] Phase-1 required, [P2]/[P3] deferred, [RISK] flagged conflict/limit.

Requirements use EARS-style phrasing. Each has acceptance criteria that a test can check.

---

## 1. File ingestion & validation

**R1.1 [MVP]** The system SHALL accept uploads of plain text (.txt), CSV, XLSX, and JSON.
- AC: Each of the four types parses into an internal table/record model; an
  unsupported extension/content is rejected with a safe message.

**R1.2 [MVP]** WHEN a file exceeds the configured size limit, the system SHALL reject it
before parsing.
- AC: A file over the limit returns a 413-style error and is never parsed.

**R1.3 [MVP]** The system SHALL validate file type by content, not extension alone.
- AC: A `.csv` that is actually a zip/binary is rejected.

**R1.4 [MVP]** WHEN an XLSX contains formulas, hidden sheets/cells, or macros, the system
SHALL NOT silently process it as safe.
- AC: Such a workbook is either rejected with an explanation OR processed only
  after extracting values to a sanitized form, and the report records this.

**R1.5 [MVP]** The system SHALL guard against decompression bombs and malicious document
content.
- AC: A crafted zip/XML bomb is rejected without exhausting memory/CPU.

---

## 2. Multi-layer detection

**R2.1 [MVP]** The system SHALL detect, via deterministic methods (regex + validators +
Presidio recognizers), at least: email, phone, US SSN, credit card (Luhn-checked),
IBAN/bank id, IP address, date of birth, URL, and structured government ids.
- AC: On the synthetic benchmark, each listed type is detected with recall >=95%.

**R2.2 [MVP]** The system SHALL detect, via NLP (spaCy + Presidio), person names,
organizations, and locations, preserving surrounding context.
- AC: For each NLP detection the stored result includes a context snippet.

**R2.3 [MVP]** The system SHALL perform dataset-aware detection using column names, data
types, value cardinality, and value format/prefix patterns.
- AC: A column `student_id` with values like `STU-2026-00421` is flagged as a likely
  identifier even though no built-in recognizer matches that format.

**R2.4 [MVP]** The system SHALL classify each finding into at least: (1) directly
identifying PII, (2) sensitive/confidential non-PII, (3) quasi-identifier.
- AC: Age, ZIP, course enrollment are classifiable as quasi-identifiers; an API
  credential string is classifiable as sensitive non-PII.

**R2.5 [MVP]** Sensitivity SHALL be user-definable per project, not hardcoded as an
inherent property of a value.
- AC: The same column can be marked sensitive in one project and not in another.

**R2.6 [MVP]** The system SHALL let users define custom detection without code: custom
regex, sensitive column names, protected keyword dictionaries, org id formats, and
entity allowlists; and SHALL let users test a rule against example data before applying.
- AC: A user-added regex matches in a dry-run preview before being saved.

**R2.7 [MVP]** The aggregation layer SHALL merge overlapping detections, resolve conflicts,
and preserve: category, source detector, location/span, score (when available),
context, and a human-review-needed flag.
- AC: Two detectors hitting the same span produce one aggregated finding retaining
  both sources.

**R2.8 [MVP]** The system SHALL NOT present uncalibrated model scores as exact
probabilities, and SHALL surface ambiguous/high-risk findings for review.
- AC: UI shows scores as qualitative bands with a disclaimer; low-confidence items
  are marked review-needed.

**R2.9 [RISK]** The 95% recall target applies ONLY to the controlled synthetic MVP
benchmark and SHALL NOT be reported as general real-world accuracy.

---

## 3. Policy-driven transformation

**R3.1 [MVP]** The system SHALL support operators: redaction, masking, tokenization,
synthetic replacement (Faker), generalization, controlled retention.
- AC: Each operator has a unit test proving its transform on a known input.

**R3.2 [MVP]** Every transformation SHALL be governed by an explicit policy mapping
entity type or column to an operator.
- AC: No value is transformed without a matching policy rule; unmatched -> default
  action defined by the policy, recorded in the report.

**R3.3 [MVP]** The system SHALL ship presets for academic research, student records,
business analytics, AI prompt protection, and software testing, each labeled as a
starting configuration, not a compliance certification.
- AC: Selecting a preset populates editable policy rules; UI shows the disclaimer.

**R3.4 [MVP]** Synthetic replacement SHALL be consistent within a project when configured
and SHALL avoid generating real-looking credentials/financial account numbers.
- AC: Same original -> same synthetic value within a project run; a test confirms no
  valid-format credential/card is generated as a replacement.

---

## 4. Secure tokenization (vault)

**R4.1 [MVP]** Tokens SHALL be generated with a cryptographically secure RNG.
- AC: Token generation uses `secrets`; a test asserts uniqueness/entropy properties.

**R4.2 [MVP]** Token mappings SHALL be consistent within a project and isolated across
projects.
- AC: Same id -> same token within a project; different token (or no access) across
  projects. Isolation test passes.

**R4.3 [MVP]** Token mappings SHALL be stored in an encrypted vault using authenticated
encryption, never in plaintext, never in logs.
- AC: Vault file on disk is ciphertext; log scan finds no original value or key.

**R4.4 [MVP]** Detokenization SHALL require explicit authorization.
- AC: Detokenize without the project authorization secret fails.

**R4.5 [MVP]** The system SHALL support token-mapping deletion and configurable retention.
- AC: Deleting a project's vault removes its mappings; a retention setting is honored.

**R4.6 [MVP]** Reversible tokenization SHALL be described as pseudonymization, never
anonymization.

---

## 5. Privacy risk verification

**R5.1 [MVP]** After transformation the system SHALL run a second, independent detection
pass over the OUTPUT and report residual findings.
- AC: An intentionally leaked value in the output is caught by the rescan.

**R5.2 [MVP]** For structured data the system SHALL compute record uniqueness and an
optional k-anonymity assessment over user-selected quasi-identifiers, with stated
limitations.
- AC: A dataset with unique quasi-identifier combinations reports k=1 rows; the report
  states method limits.

**R5.3 [MVP]** The system SHALL check for data leakage in exports: original values in
cells, file metadata, hidden content, or unsupported fields.
- AC: A planted original value in XLSX metadata is detected and blocks/flags export.

**R5.4 [MVP]** The risk report SHALL list remaining detected info, unreviewed findings,
risky attribute combinations, transformation methods used, unprocessed content, and
assessment limitations; it SHALL NOT present a "100% safe" score.
- AC: Report contains all listed sections; no absolute-safety claim string appears.

**R5.5 [MVP]** The system SHALL block export (fail-safe) when processing failed, content
was unexamined, or critical unresolved findings remain; an authorized override path
SHALL be documented and logged.
- AC: Export is blocked in each failure condition; override requires explicit action
  and is recorded.

---

## 6. Data utility preservation

**R6.1 [MVP]** For structured data the system SHALL preserve data types, row/column
relationships, and valid joins when consistent tokens are used, and SHALL avoid
changing non-sensitive values.
- AC: A join key tokenized consistently still joins across two files; non-targeted
  columns are byte-identical before/after.

**R6.2 [MVP]** The system SHALL produce a data-quality comparison: row/column counts,
missing values before/after, numeric distributions where relevant, changed fields,
and potentially broken relationships.
- AC: The comparison report is generated and matches a hand-checked fixture.

---

## 7. User experience

**R7.1 [MVP]** The system SHALL provide pages: Dashboard, Upload Workspace, Detection
Review, Privacy Policy Editor, Before/After Preview, Verification Report, Export.
- AC: Each page renders and drives the real backend (no mocked results).

**R7.2 [MVP]** Detection Review SHALL show original data in a controlled preview with
highlighted entities, categories, explanations, confidence bands, and tools to correct
false positives and add missed identifiers.
- AC: A user can delete a false positive and add a missed span; both persist.

**R7.3 [MVP]** The UI SHALL be usable by nontechnical users while exposing advanced
controls; it SHALL be accessible (keyboard nav, labels, contrast).
- AC: Automated a11y check passes on each page.

---

## 8. Security & privacy (cross-cutting)

**R8.1-R8.x [MVP]** All rules in `.kiro/steering/security.md` are requirements:
local-by-default, no data telemetry, no raw sensitive values in logs, safe temp-file
handling, size/resource limits, content-type validation, no hardcoded keys, encrypted
mappings, project isolation, safe error messages, uploaded text treated as data.
- AC: Each has a corresponding test or documented control; see test matrix in tasks.md.

---

## 9. Deliverables

**R9.1 [MVP]** requirements.md, design.md, tasks.md, functional MVP codebase, dependency
& env config, setup/run instructions, automated tests + benchmark report, sample
synthetic university dataset, security-limitations document, and a Phase 2/3 roadmap.

---

## 10. Explicit conflicts / impossible guarantees (flagged for the user)

- **C1** "95% recall" is only meaningful on a defined benchmark; stated as benchmark-only.
- **C2** Tokenization is reversible => pseudonymization, not anonymization. Cannot be
  sold as anonymization.
- **C3** No tool can guarantee perfect de-identification; the product must not claim it.
- **C4** k-anonymity and uniqueness analysis are heuristics with real limits; reported
  with caveats, not as proof of safety.
- **C5** Safe PDF/scanned-doc redaction is NOT in Phase 1 (deferred to P2) because
  trustworthy underlying-text removal is non-trivial; drawing black boxes is forbidden.
- **C6** Legal compliance (FERPA/HIPAA/GDPR) is NOT certified; presets are starting points.
