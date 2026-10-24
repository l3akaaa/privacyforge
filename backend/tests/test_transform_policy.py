import re

import pytest

from privacyforge.policy import PRESETS, Policy, PolicyRule, get_preset
from privacyforge.transform import Transformer
from privacyforge.vault import TokenVault
from privacyforge.models import Category, Finding


@pytest.fixture(autouse=True)
def _master_key(monkeypatch):
    monkeypatch.setenv("PRIVACYFORGE_MASTER_KEY", "test-master-key")


def test_redact():
    t = Transformer()
    assert t.redact("John Smith", "PERSON") == "[REDACTED_PERSON]"


def test_mask():
    t = Transformer()
    assert t.mask("12345678", visible=2) == "12******"


def test_synthetic_consistent_and_not_a_card():
    t = Transformer()
    a = t.synthetic("John Smith", "PERSON")
    b = t.synthetic("John Smith", "PERSON")
    assert a == b
    # Generic entity must never produce a valid-looking card number.
    out = t.synthetic("4111111111111111", "ACCOUNT_NUMBER")
    assert not re.fullmatch(r"[\d \-]{13,19}", out)


def test_generalize_age_and_date():
    t = Transformer()
    assert "-" in t.generalize("19", mode="age")
    assert t.generalize("October 12, 2006", mode="year") == "2006"


def test_tokenize_via_vault(tmp_path):
    v = TokenVault("p1", tmp_path)
    t = Transformer(vault=v)
    tok = t.apply("tokenize", "STU-001", "STUDENT_ID", {})
    assert tok.startswith("TOK_")


def test_policy_resolution_precedence():
    pol = Policy(
        rules=[
            PolicyRule(match_type="category", match_value="pii", operator="redact"),
            PolicyRule(match_type="entity", match_value="STUDENT_ID", operator="tokenize"),
        ],
        default_operator="mask",
    )
    f = Finding(entity_type="STUDENT_ID", category=Category.PII, source="column", field="sid")
    op, _ = pol.resolve(f)
    assert op == "tokenize"  # entity rule beats category rule


def test_presets_have_disclaimer():
    for name in PRESETS:
        p = get_preset(name)
        assert p and "not a legal-compliance certification" in p.disclaimer
