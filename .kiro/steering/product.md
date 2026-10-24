# PrivacyForge -- Product Mission

## What it is
PrivacyForge is a privacy-first, local-by-default data de-identification platform.
It helps students, researchers, universities, and companies process sensitive
datasets (CSV, XLSX, JSON, plain text to start) by detecting likely sensitive
information, transforming it under an explicit user-chosen policy, and verifying
the result with an independent second scan.

## Who it is for
- Nontechnical users (students, researchers) who need a simple guided workflow.
- Technical users (engineers, privacy officers) who need advanced controls,
  custom detection rules, and auditable transformations.

## Core promises (and honest limits)
PrivacyForge DOES:
- Run multiple complementary detection methods (deterministic, NLP, dataset-aware,
  contextual, user-defined custom rules), then aggregate and deduplicate them.
- Let the user review, correct, and extend detections before any change.
- Transform data by an explicit policy: redact, mask, tokenize, synthetic
  replacement, generalize, or controlled retention.
- Tokenize consistently within a project scope using cryptographically secure
  randomness, with an encrypted vault and authorized-only detokenization.
- Run a second independent privacy scan and a transparent risk report.
- Preserve data utility (types, relationships, joins) where policy allows.

PrivacyForge DOES NOT, and must never claim to:
- Guarantee perfect or "100% safe" de-identification.
- Certify legal compliance (HIPAA, FERPA, GDPR). Presets are starting points only.
- Treat reversible tokenization as anonymization -- it is pseudonymization.
- Present model confidence scores as exact probabilities of identification.

## The flagship workflow (MVP definition of done)
Upload a synthetic university dataset -> detect common + university-specific
identifiers -> explain findings -> user reviews/corrects -> tokenize student IDs
consistently -> redact/replace names & emails per policy -> preserve GPA and
permitted attributes and relationships -> residual-PII rescan -> risk report with
limitations -> export transformed dataset + audit report. Driven through real UI
and real backend logic, never canned output.

## Non-negotiable
Correctness, privacy, and security over feature count. Never silently mark an
unfinished feature as done. Always distinguish implemented / partial / planned.
