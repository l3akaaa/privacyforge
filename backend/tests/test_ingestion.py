import io
import zipfile

import pytest

from privacyforge.errors import FileTooLargeError, UnsupportedFileError
from privacyforge.ingestion import parse_csv, parse_json, parse_txt, parse_upload


def test_parse_csv_basic():
    data = b"name,email\nJane,jane@x.edu\nBob,bob@y.edu\n"
    ds = parse_csv(data)
    assert ds.column_names == ["name", "email"]
    assert len(ds.rows) == 2


def test_parse_json_list():
    data = b'[{"a":1,"b":2},{"a":3,"b":4}]'
    ds = parse_json(data)
    assert ds.column_names == ["a", "b"]
    assert len(ds.rows) == 2


def test_csv_rejects_binary_masquerade():
    # Zip magic bytes inside a .csv -> rejected.
    with pytest.raises(UnsupportedFileError):
        parse_csv(b"PK\x03\x04rest-of-binary")


def test_size_limit(monkeypatch):
    import privacyforge.config as cfg
    monkeypatch.setattr(cfg, "MAX_FILE_BYTES", 10)
    with pytest.raises(FileTooLargeError):
        parse_txt(b"this is definitely longer than ten bytes")


def test_json_invalid_rejected():
    with pytest.raises(UnsupportedFileError):
        parse_json(b"not json at all")


def test_dtype_inference():
    data = b"id,score\n1,3.5\n2,4.0\n"
    ds = parse_csv(data)
    score = next(c for c in ds.columns if c.name == "score")
    assert score.dtype == "number"


def test_unsupported_extension():
    with pytest.raises(UnsupportedFileError):
        parse_upload("data.exe", b"\x4d\x5a binary")
