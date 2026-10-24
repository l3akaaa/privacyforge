"""File ingestion & validation (Milestone 1; Requirements R1.1-R1.5).

Parses TXT/CSV/JSON/XLSX into typed models, validating by content (not just
extension), enforcing size and resource limits, and refusing unsafe workbooks
and decompression bombs.
"""
from __future__ import annotations

import csv
import io
import json
import zipfile
from typing import Any

from . import config
from .errors import FileTooLargeError, UnsafeFileError, UnsupportedFileError
from .models import ColumnSchema, Dataset, TextDoc

_XLSX_MAGIC = b"PK\x03\x04"  # zip-based


def _check_size(data: bytes) -> None:
    if len(data) > config.MAX_FILE_BYTES:
        raise FileTooLargeError(
            f"File exceeds the {config.MAX_FILE_BYTES // (1024 * 1024)} MB limit."
        )


def _infer_dtype(values: list[str]) -> str:
    seen_num = seen_other = False
    for v in values:
        if v == "" or v is None:
            continue
        try:
            float(v)
            seen_num = True
        except (TypeError, ValueError):
            seen_other = True
    if seen_num and not seen_other:
        return "number"
    if seen_num and seen_other:
        return "mixed"
    return "string"


def _dataset_from_records(records: list[dict[str, Any]], kind: str) -> Dataset:
    if len(records) > config.MAX_ROWS:
        raise UnsafeFileError("Row count exceeds the configured limit.")
    # Preserve first-seen column order across all records.
    col_order: list[str] = []
    for rec in records:
        for k in rec.keys():
            if k not in col_order:
                col_order.append(k)
    if len(col_order) > config.MAX_COLS:
        raise UnsafeFileError("Column count exceeds the configured limit.")
    columns = [
        ColumnSchema(name=c, dtype=_infer_dtype([str(r.get(c, "")) for r in records]))
        for c in col_order
    ]
    norm = [{c: rec.get(c) for c in col_order} for rec in records]
    return Dataset(columns=columns, rows=norm, kind=kind)  # type: ignore[arg-type]


def parse_txt(data: bytes) -> TextDoc:
    _check_size(data)
    return TextDoc(text=data.decode("utf-8", errors="replace"))


def parse_csv(data: bytes) -> Dataset:
    _check_size(data)
    text = data.decode("utf-8-sig", errors="replace")
    # Reject content that is actually a binary/zip masquerading as CSV.
    if data[:4] == _XLSX_MAGIC or b"\x00" in data[:1024]:
        raise UnsupportedFileError("File content is not valid CSV text.")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise UnsupportedFileError("CSV has no header row.")
    records = []
    for i, row in enumerate(reader):
        if i >= config.MAX_ROWS:
            raise UnsafeFileError("Row count exceeds the configured limit.")
        records.append(dict(row))
    return _dataset_from_records(records, "csv")


def parse_json(data: bytes) -> Dataset:
    _check_size(data)
    try:
        obj = json.loads(data.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise UnsupportedFileError("File is not valid JSON.") from exc
    if isinstance(obj, dict):
        obj = [obj]
    if not isinstance(obj, list) or not all(isinstance(r, dict) for r in obj):
        raise UnsupportedFileError("JSON must be an object or a list of objects.")
    return _dataset_from_records(obj, "json")


def parse_xlsx(data: bytes) -> tuple[Dataset, list[str]]:
    """Parse XLSX safely. Returns (dataset, warnings).

    Refuses non-zip content, guards against decompression bombs, and flags
    formulas / hidden sheets / macros. Values are extracted (never formulas),
    so a formula cannot silently leak its source (R1.4).
    """
    _check_size(data)
    if data[:4] != _XLSX_MAGIC:
        raise UnsupportedFileError("File content is not a valid XLSX workbook.")

    # Decompression-bomb guard using the zip directory.
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise UnsafeFileError("Workbook is corrupt or not a valid zip.") from exc
    total_uncompressed = sum(info.file_size for info in zf.infolist())
    if len(data) > 0 and total_uncompressed > len(data) * config.MAX_DECOMPRESS_RATIO:
        raise UnsafeFileError("Workbook rejected: decompression-bomb ratio exceeded.")
    names = zf.namelist()

    warnings: list[str] = []
    if any(n.lower().endswith(".bin") or "vbaproject" in n.lower() for n in names):
        warnings.append("Workbook contains macros/binary parts; those were not processed.")

    import openpyxl  # local import keeps base import light

    # data_only=True returns last cached values, never formula strings.
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    for ws in wb.worksheets:
        if ws.sheet_state != "visible":
            warnings.append(f"Hidden sheet '{ws.title}' was skipped.")

    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    try:
        header = next(rows_iter)
    except StopIteration:
        raise UnsupportedFileError("Workbook has no data.") from None
    headers = [str(h) if h is not None else f"col_{i}" for i, h in enumerate(header)]
    records: list[dict[str, Any]] = []
    for i, row in enumerate(rows_iter):
        if i >= config.MAX_ROWS:
            raise UnsafeFileError("Row count exceeds the configured limit.")
        records.append({headers[j]: row[j] if j < len(row) else None
                        for j in range(len(headers))})
    wb.close()
    return _dataset_from_records(records, "xlsx"), warnings


def parse_upload(filename: str, data: bytes) -> tuple[object, list[str]]:
    """Dispatch by content + extension. Returns (Dataset|TextDoc, warnings)."""
    lower = filename.lower()
    if lower.endswith(".xlsx") or data[:4] == _XLSX_MAGIC:
        return parse_xlsx(data)
    if lower.endswith(".json"):
        return parse_json(data), []
    if lower.endswith(".csv"):
        return parse_csv(data), []
    if lower.endswith(".txt"):
        return parse_txt(data), []
    # Fall back to content sniffing.
    stripped = data.lstrip()[:1]
    if stripped in (b"{", b"["):
        return parse_json(data), []
    raise UnsupportedFileError("Unsupported file type. Use TXT, CSV, XLSX, or JSON.")
