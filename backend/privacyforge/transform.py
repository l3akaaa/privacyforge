"""Transformation engine (Milestone 4; Requirements R3.1, R3.4).

Pure operators over a value + params + optional vault. Synthetic replacement is
consistent within a project and guarded against producing valid credentials.
"""
from __future__ import annotations

import hashlib
import re
from typing import Optional

from faker import Faker

from .policy import Operator
from .vault import TokenVault


class Transformer:
    def __init__(self, vault: Optional[TokenVault] = None, project_seed: str = "pf") -> None:
        self.vault = vault
        self._faker = Faker()
        self._project_seed = project_seed
        self._synthetic_cache: dict[tuple[str, str], str] = {}

    # ---- operators ------------------------------------------------------

    def redact(self, value: str, entity_type: str) -> str:
        return f"[REDACTED_{entity_type}]"

    def mask(self, value: str, visible: int = 2, char: str = "*") -> str:
        v = str(value)
        if len(v) <= visible:
            return char * len(v)
        return v[:visible] + char * (len(v) - visible)

    def tokenize(self, value: str) -> str:
        if self.vault is None:
            raise ValueError("Tokenize requires a vault.")
        return self.vault.tokenize(str(value))

    def _seeded_faker(self, value: str, entity_type: str) -> Faker:
        # Deterministic per (project, value) so repeats map consistently.
        seed = int(hashlib.sha256(
            (self._project_seed + "|" + entity_type + "|" + value).encode()
        ).hexdigest(), 16) % (2**32)
        f = Faker()
        f.seed_instance(seed)
        return f

    def synthetic(self, value: str, entity_type: str) -> str:
        key = (entity_type, str(value))
        if key in self._synthetic_cache:
            return self._synthetic_cache[key]
        f = self._seeded_faker(str(value), entity_type)
        et = entity_type.upper()
        if "EMAIL" in et:
            out = f.email()
        elif "PERSON" in et or "NAME" in et:
            out = f.name()
        elif "PHONE" in et:
            out = f.numerify("###-###-####")  # format only, not a real line
        elif "LOCATION" in et or "ADDRESS" in et or "GPE" in et:
            out = f.city()
        elif "ORG" in et:
            out = f.company()
        else:
            # Generic token-like replacement; never emit a valid card/SSN.
            out = "SYN_" + f.lexify("??????").upper()
        # Guard: never return something that looks like a valid credit card/SSN.
        if re.fullmatch(r"[\d \-]{13,19}", out) or re.fullmatch(r"\d{3}-\d{2}-\d{4}", out):
            out = "SYN_" + f.lexify("??????").upper()
        self._synthetic_cache[key] = out
        return out

    def generalize(self, value: str, mode: str = "auto") -> str:
        v = str(value).strip()
        # Age -> range.
        if v.isdigit() and mode in ("auto", "age"):
            n = int(v)
            if 0 <= n <= 120:
                lo = (n // 6) * 6
                return f"{lo}-{lo + 5}"
        # Date -> year or month/year.
        m = re.search(r"(\d{4})", v)
        if m and mode in ("auto", "year", "month"):
            return m.group(1)
        # ZIP -> prefix.
        if re.fullmatch(r"\d{5}(-\d{4})?", v):
            return v[:3] + "XX"
        return "[GENERALIZED]"

    def retain(self, value: str) -> str:
        return str(value)

    # ---- dispatch -------------------------------------------------------

    def apply(self, operator: Operator, value: str, entity_type: str, params: dict) -> str:
        if value is None:
            return value
        if operator == "redact":
            return self.redact(value, entity_type)
        if operator == "mask":
            return self.mask(value, int(params.get("visible", 2)))
        if operator == "tokenize":
            return self.tokenize(value)
        if operator == "synthetic":
            return self.synthetic(value, entity_type)
        if operator == "generalize":
            return self.generalize(value, params.get("mode", "auto"))
        if operator == "retain":
            return self.retain(value)
        raise ValueError(f"Unknown operator: {operator}")
