# PrivacyForge -- Coding Standards & Testing Expectations

## Python (backend)
- Python 3.12. Format with `ruff format`; lint with `ruff`. Type hints required
  on public functions; check with `mypy` where practical.
- Pydantic models for all API request/response bodies.
- Pure functions for detection/transform logic so they test without the web layer.
- No bare `except`. Raise typed errors; map to safe HTTP responses at the edge.
- Docstrings state what a function guarantees and, crucially, what it does NOT.

## TypeScript (frontend)
- Strict TypeScript. ESLint + Prettier. Tailwind for styling.
- Accessible components (labels, roles, keyboard nav, visible focus).
- No detection/transformation logic in the client -- call the API.

## Testing (every feature ships with tests)
- Unit tests for each detector and transform operator (pure logic).
- API integration tests for each endpoint.
- End-to-end test for the flagship university workflow.
- A benchmark suite over synthetic datasets with KNOWN labels, reporting
  precision / recall / F1 per entity category and per scenario, plus explicit
  false-negative counts.
- Preliminary target: >=95% recall on the controlled synthetic MVP benchmark.
  This is reported as benchmark-only, never as real-world accuracy. If missed,
  report real numbers, analyze failures, fix -- never fabricate.
- Isolation tests: project A cannot read project B's tokens or files.
- Failure tests: corrupted/malicious/unsupported files are rejected safely.

## Definition of done for a task
Working code + passing tests + task status updated + limitations stated.
No placeholder/hardcoded outputs standing in for real processing.
