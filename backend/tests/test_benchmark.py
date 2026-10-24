from privacyforge.benchmark import run


def test_deterministic_core_recall_and_precision(monkeypatch):
    monkeypatch.setenv("PRIVACYFORGE_MASTER_KEY", "x")
    result = run(use_nlp=False)
    # Zero false positives on the controlled set (validators reject look-alikes).
    assert result["totals"]["fp"] == 0
    # Excluding NLP-only scenarios, the deterministic core catches everything.
    assert result["recall_excluding_nlp_scenarios"] == 1.0


def test_benign_lookalike_not_flagged(monkeypatch):
    monkeypatch.setenv("PRIVACYFORGE_MASTER_KEY", "x")
    result = run(use_nlp=False)
    look = next(s for s in result["scenarios"] if s["scenario"] == "8_benign_lookalike")
    assert "CREDIT_CARD" not in look["found"]
