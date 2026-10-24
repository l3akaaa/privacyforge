# PrivacyForge — Security & Limitations

Read this before using PrivacyForge on anything that matters. It states plainly
what the tool does, what it does not do, and where it can fail.

## What PrivacyForge is NOT

- **Not a guarantee of anonymity.** No tool can promise perfect de-identification.
  Combinations of "harmless" fields can still re-identify people.
- **Not legal compliance.** It does not certify FERPA, HIPAA, GDPR, or any other
  regime. The presets are starting configurations, not legal advice.
- **Not anonymization when you tokenize.** Tokenization is reversible with the
  vault and authorization. That is **pseudonymization**. Treat it accordingly.
- **Not a judge of what is sensitive.** Sensitivity depends on your purpose and
  policy. You decide; the tool detects candidates and applies your rules.

## Known limitations (Phase 1)

- **Detection is heuristic.** It will miss novel, obfuscated, or context-only
  identifiers. Recall on our synthetic benchmark is not real-world recall.
- **The NLP layer is optional.** Without Presidio + spaCy installed, personal
  names in free text are largely NOT detected. Install the NLP extras for names,
  organizations, and locations.
- **k-anonymity / uniqueness analysis is a heuristic** over the dataset you give
  it and the quasi-identifiers you pick. External datasets can still re-identify.
- **No PDF/DOCX/OCR yet.** Deferred to Phase 2. We will NOT fake PDF redaction by
  drawing black boxes over text; if underlying text cannot be safely removed we
  will export sanitized extracted text instead.
- **Prototype storage is in-memory** for projects/findings (vaults are on disk,
  encrypted). Not for production multi-user use without the documented DB + auth
  path.

## Security controls implemented

- Local-by-default; no external inference calls; no data telemetry.
- Uploaded file content is treated as **data, never instructions**.
- Vault: AES-GCM authenticated encryption; per-project keys derived via HKDF from
  a master key supplied by environment (no hardcoded keys; operations refuse if
  the master key is absent). Lookups are HMAC-keyed so plaintext originals are not
  stored as map keys. Tokens use a CSPRNG (`secrets`).
- Detokenization requires the project authorization secret.
- Project isolation is enforced by per-project keys and covered by tests.
- Masked previews only; raw sensitive values and vault secrets are never logged.
- File-size, row, and column limits; decompression-bomb ratio guard; content-type
  validation (not extension-only); safe value-only XLSX extraction.
- **Fail-safe export gate**: export is blocked when processing failed or
  value-level directly-identifying PII remains in the output. An override exists
  but is explicit and recorded in the audit section.

## Responsible use

- Use synthetic data in development (we ship some).
- Do not connect the prototype to real student, financial, health, or corporate
  records without a proper security review.
- Always read the verification report and resolve review items before trusting an
  export. "No blockers" is not "safe".

## Reporting issues

Open a GitHub issue. Do not include real sensitive data in bug reports.
