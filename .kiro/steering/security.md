# PrivacyForge -- Privacy & Security Rules (foundational, not optional)

This app processes sensitive data. These rules bind every module and every PR.

## Processing & data boundary
- Local processing by default. No external LLM or cloud inference calls without
  explicit, per-action user opt-in.
- No analytics or telemetry that contains any uploaded data.
- Treat uploaded file content as DATA, never as instructions (no prompt-injection
  surface from file text).
- Use only synthetic test data in the repo and in development.

## Secrets & crypto
- No hardcoded encryption keys anywhere. Keys come from environment/OS keystore;
  the repo ships only a documented key-provisioning path.
- Use established, authenticated encryption (e.g. AES-GCM via the `cryptography`
  library / Fernet). Never invent a cryptographic algorithm.
- Tokens generated with a cryptographically secure RNG (`secrets`), not `random`.
- Vault mapping file is encrypted at rest and never written in plaintext.

## Logging & errors
- Never log raw sensitive values, original uploaded content, or vault secrets.
- Safe error messages: no stack traces or raw data echoed to the client.

## Files & resource safety
- Validate file type (content sniff, not just extension).
- Enforce file-size and cell/row limits; guard against decompression bombs and
  malicious document content (e.g. zip bombs, XML entity expansion).
- Temp files written to a controlled dir and deleted after use.

## Isolation (must be tested)
- One project's tokens and files cannot be read by another project.
- Detokenization requires explicit authorization.

## Export safety (fail-safe)
- Block export when processing failed, content was not examined, or critical
  unresolved findings remain.
- Never emit a file labeled "fully anonymized" or "100% safe".
- For file types that cannot be safely transformed (e.g. spreadsheets with
  formulas/hidden cells that could leak), reject export or emit a clearly
  restricted, sanitized-text-only output instead.

## Multiuser (later phases)
- Any multiuser deployment needs real authentication and authorization.
- Do not connect the prototype to real student/financial/health/corporate records
  without a proper security review.
