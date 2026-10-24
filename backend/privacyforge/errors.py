"""Typed errors mapped to safe HTTP responses at the API edge (R8 safe errors)."""
from __future__ import annotations


class PrivacyForgeError(Exception):
    """Base error. The `message` is safe to show the user (no raw data)."""

    code = "error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UnsupportedFileError(PrivacyForgeError):
    code = "unsupported_file"


class FileTooLargeError(PrivacyForgeError):
    code = "file_too_large"


class UnsafeFileError(PrivacyForgeError):
    code = "unsafe_file"


class VaultError(PrivacyForgeError):
    code = "vault_error"


class AuthorizationError(PrivacyForgeError):
    code = "not_authorized"


class ExportBlockedError(PrivacyForgeError):
    code = "export_blocked"
