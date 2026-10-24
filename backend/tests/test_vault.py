import os

import pytest

from privacyforge.errors import AuthorizationError, VaultError
from privacyforge.vault import TokenVault


@pytest.fixture(autouse=True)
def _master_key(monkeypatch):
    monkeypatch.setenv("PRIVACYFORGE_MASTER_KEY", "test-master-key-not-for-production")


def test_refuses_without_master_key(monkeypatch, tmp_path):
    monkeypatch.delenv("PRIVACYFORGE_MASTER_KEY", raising=False)
    with pytest.raises(VaultError):
        TokenVault("p1", tmp_path)


def test_tokenize_is_consistent(tmp_path):
    v = TokenVault("p1", tmp_path)
    t1 = v.tokenize("STUDENT_001")
    t2 = v.tokenize("STUDENT_001")
    assert t1 == t2
    assert t1.startswith("TOK_")
    assert v.tokenize("STUDENT_002") != t1


def test_project_isolation(tmp_path):
    a = TokenVault("projA", tmp_path)
    b = TokenVault("projB", tmp_path)
    ta = a.tokenize("SAME_VALUE")
    tb = b.tokenize("SAME_VALUE")
    # Different projects produce different tokens and cannot cross-detokenize.
    assert ta != tb
    with pytest.raises((AuthorizationError, VaultError)):
        b.detokenize(ta, b.authorization_secret())


def test_no_plaintext_on_disk(tmp_path):
    v = TokenVault("p1", tmp_path)
    v.tokenize("SECRET_ID_12345")
    blob = (tmp_path / "p1.vault").read_bytes()
    assert b"SECRET_ID_12345" not in blob


def test_detokenize_requires_authorization(tmp_path):
    v = TokenVault("p1", tmp_path)
    tok = v.tokenize("STUDENT_001")
    with pytest.raises(AuthorizationError):
        v.detokenize(tok, "wrong-secret")
    assert v.detokenize(tok, v.authorization_secret()) == "STUDENT_001"


def test_delete_removes_mappings(tmp_path):
    v = TokenVault("p1", tmp_path)
    v.tokenize("X")
    v.delete()
    assert not (tmp_path / "p1.vault").exists()


def test_wrong_key_refuses_by_default(tmp_path, monkeypatch):
    # Create a vault with one key, then reopen with a different key -> refuse.
    monkeypatch.setenv("PRIVACYFORGE_MASTER_KEY", "key-A")
    v = TokenVault("p1", tmp_path)
    v.tokenize("VALUE")
    monkeypatch.setenv("PRIVACYFORGE_MASTER_KEY", "key-B")
    import pytest as _pytest
    with _pytest.raises(VaultError):
        TokenVault("p1", tmp_path)


def test_wrong_key_resets_when_flag_set(tmp_path, monkeypatch):
    monkeypatch.setenv("PRIVACYFORGE_MASTER_KEY", "key-A")
    v = TokenVault("p1", tmp_path)
    v.tokenize("VALUE")
    monkeypatch.setenv("PRIVACYFORGE_MASTER_KEY", "key-B")
    monkeypatch.setenv("PRIVACYFORGE_VAULT_RESET", "1")
    v2 = TokenVault("p1", tmp_path)  # should start fresh, not raise
    # Fresh vault: a new tokenize works.
    assert v2.tokenize("NEW").startswith("TOK_")
