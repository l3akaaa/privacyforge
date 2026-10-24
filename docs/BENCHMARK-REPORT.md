# PrivacyForge — Detection Benchmark Report

**Scope:** a controlled, fully synthetic benchmark with known labels. These
numbers describe performance on THIS benchmark only. They are **not** a measure
of real-world accuracy. Regenerate with `python -m privacyforge.benchmark`
(raw output saved to `benchmark_output.json`).

## Headline results (deterministic + dataset-aware + custom layers; NLP NOT installed)

| Metric | Value |
|--------|-------|
| Precision | 100% |
| Recall (overall) | 87.5% |
| Recall (excluding NLP-only scenarios) | 100% |
| F1 (overall) | 93.3% |
| False positives | 0 |

## Per-scenario

| Scenario | Expected | Detected without NLP | Result |
|----------|----------|----------------------|--------|
| Email + phone | EMAIL, PHONE | both | pass |
| Name in a sentence | PERSON | — | **miss (needs NLP layer)** |
| Org-specific student ID (column) | STUDENT_ID | STUDENT_ID | pass |
| ID without a label (custom rule) | BADGE | BADGE | pass |
| Benign look-alike (invalid Luhn) | (nothing) | nothing | pass (no false positive) |
| US SSN | US_SSN | US_SSN | pass |
| Credit card (valid Luhn) | CREDIT_CARD | CREDIT_CARD | pass |
| IP address | IP_ADDRESS | IP_ADDRESS | pass |

## Failure analysis

- **Name in a sentence → miss.** Personal names in free text require the optional
  NLP layer (Presidio + spaCy). Without it, the deterministic layers do not detect
  arbitrary names. **Fix:** install `requirements-nlp.txt` +
  `python -m spacy download en_core_web_lg`. With NLP enabled, this scenario is
  expected to pass and overall recall reaches the synthetic target.

## Why precision is 100% here

The deterministic layer validates candidates (Luhn for credit cards, structural
rules for SSNs), so the invalid-Luhn "order number" look-alike is correctly NOT
flagged. This is by design: validators reduce false positives.

## Honesty note

The brief set a preliminary target of ≥95% recall **on this controlled synthetic
benchmark**. Without the NLP layer the core reaches 87.5% overall (100% on the
non-NLP scenarios). We report the real number rather than inflate it; the gap is
fully explained by the optional NLP dependency above, not by a detector defect.
