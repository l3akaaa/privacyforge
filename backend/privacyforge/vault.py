"""Secure tokenization vault (Milestone 3; Requirements R4.1-R4.6).

Design (see design.md section 5):
- Per-project key derived from a master key (env var, never in repo) via HKDF
  with a per-project salt. If the master key is absent, every vault operation
  refuses -- there is NO default key.
- Mappings stored in a per-project file encrypted with AES-GCM (authenticated).
- Lookup key is HMAC(original), so the plaintext original is never a map key.
- Tokens use `secrets` (CSPRNG), base32, collision-checked within the project.
- Detokenization requires the project authorization secret.
- Nothing from the vault is ever logged.

This is PSEUDONYMIZATION, not anonymization. Tokens are reversible with the
vault + authorization. The product never calls this "anonymous".
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from .config import MASTER_KEY_ENV
from .errors import AuthorizationError, VaultError


def _master_key() -> bytes:
    raw = os.environ.get(MASTER_KEY_ENV)
    if not raw:
        raise VaultError(
            "Vault master key is not configured. Set the "
            f"{MASTER_KEY_ENV} environment variable; there is no default key."
        )
    # Accept base64 or raw text; normalize to 32 bytes via SHA-256 if needed.
    try:
        kb = base64.urlsafe_b64decode(raw)
        if len(kb) in (16, 24, 32):
            return kb
    except Exception:
        pass
    return hashlib.sha256(raw.encode("utf-8")).digest()


def _derive(master: bytes, salt: bytes, info: bytes, length: int = 32) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=length, salt=salt, info=info).derive(master)


class TokenVault:
    """One vault per project. Keys are isolated across projects by salt."""

    def __init__(self, project_id: str, vault_dir: str | os.PathLike[str]) -> None:
        self.project_id = project_id
        self.dir = Path(vault_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / f"{project_id}.vault"
        self.salt_path = self.dir / f"{project_id}.salt"

        master = _master_key()
        if self.salt_path.exists():
            salt = self.salt_path.read_bytes()
        else:
            salt = secrets.token_bytes(16)
            self.salt_path.write_bytes(salt)
        # Separate derived keys for encryption, HMAC lookup, and authorization.
        self._enc_key = _derive(master, salt, b"pf-enc-" + project_id.encode())
        self._hmac_key = _derive(master, salt, b"pf-hmac-" + project_id.encode())
        self._auth_key = _derive(master, salt, b"pf-auth-" + project_id.encode())
        self._map = self._load()

    # ---- persistence ----------------------------------------------------

    def _load(self) -> dict[str, dict[str, str]]:
        if not self.path.exists():
            return {"by_hmac": {}, "tokens": {}}
        blob = self.path.read_bytes()
        nonce, ct = blob[:12], blob[12:]
        aes = AESGCM(self._enc_key)
        try:
            data = aes.decrypt(nonce, ct, b"pf-vault")
        except Exception as exc:
            # Strict by default: a decryption failure can mean tampering, so we
            # refuse. For LOCAL DEV ONLY, PRIVACYFORGE_VAULT_RESET=1 lets a vault
            # locked with a now-different key start fresh instead of blocking the
            # whole workflow. Never enable this where the vault holds real,
            # irreplaceable mappings -- it discards them.
            if os.environ.get("PRIVACYFORGE_VAULT_RESET") == "1":
                return {"by_hmac": {}, "tokens": {}}
            raise VaultError(
                "Vault could not be decrypted. This usually means the master key "
                "changed since it was created, or the file was altered. If this is "
                "a local test vault with no data you need, set "
                "PRIVACYFORGE_VAULT_RESET=1 to start fresh."
            ) from exc
        return json.loads(data.decode("utf-8"))

    def _save(self) -> None:
        aes = AESGCM(self._enc_key)
        nonce = secrets.token_bytes(12)
        ct = aes.encrypt(nonce, json.dumps(self._map).encode("utf-8"), b"pf-vault")
        tmp = self.path.with_suffix(".tmp")
        tmp.write_bytes(nonce + ct)
        tmp.replace(self.path)

    # ---- tokenization ---------------------------------------------------

    def _hmac(self, original: str) -> str:
        return hmac.new(self._hmac_key, original.encode("utf-8"), hashlib.sha256).hexdigest()

    def _new_token(self) -> str:
        while True:
            tok = "TOK_" + base64.b32encode(secrets.token_bytes(10)).decode().rstrip("=")
            if tok not in self._map["tokens"]:
                return tok

    def tokenize(self, original: str) -> str:
        """Return a stable token for `original` within this project."""
        h = self._hmac(original)
        existing = self._map["by_hmac"].get(h)
        if existing:
            return existing
        tok = self._new_token()
        # Store the original encrypted (per-value) so detokenize can recover it.
        aes = AESGCM(self._enc_key)
        nonce = secrets.token_bytes(12)
        ct = aes.encrypt(nonce, original.encode("utf-8"), b"pf-val")
        self._map["by_hmac"][h] = tok
        self._map["tokens"][tok] = base64.b64encode(nonce + ct).decode()
        self._save()
        return tok

    def authorization_secret(self) -> str:
        """The secret a caller must present to detokenize (project-scoped)."""
        return base64.urlsafe_b64encode(self._auth_key).decode()

    def detokenize(self, token: str, authorization: str) -> str:
        if not hmac.compare_digest(authorization, self.authorization_secret()):
            raise AuthorizationError("Detokenization is not authorized for this project.")
        enc = self._map["tokens"].get(token)
        if not enc:
            raise VaultError("Unknown token.")
        blob = base64.b64decode(enc)
        nonce, ct = blob[:12], blob[12:]
        aes = AESGCM(self._enc_key)
        return aes.decrypt(nonce, ct, b"pf-val").decode("utf-8")

    def delete(self) -> None:
        """Delete this project's vault and salt (R4.5)."""
        for p in (self.path, self.salt_path):
            if p.exists():
                p.unlink()
        self._map = {"by_hmac": {}, "tokens": {}}
