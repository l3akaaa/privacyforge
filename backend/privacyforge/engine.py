"""Processing engine: apply policy + transforms to a Dataset/TextDoc.

Ties detection -> policy resolution -> transform. Produces the transformed
output plus a record of which cells changed and which operator was used.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .models import Dataset, Finding, TextDoc
from .policy import Policy
from .transform import Transformer


@dataclass
class TransformResult:
    dataset: Optional[Dataset] = None
    textdoc: Optional[TextDoc] = None
    changed_cells: list[tuple[int, str]] = field(default_factory=list)  # (row, col)
    operators_used: dict[str, str] = field(default_factory=dict)        # entity/col -> op
    change_count: int = 0


def apply_to_dataset(
    ds: Dataset,
    findings: list[Finding],
    policy: Policy,
    transformer: Transformer,
) -> TransformResult:
    # Only act on findings the user has not removed and that are column-scoped
    # or cell-scoped. Column-level findings transform the whole column.
    result = TransformResult(operators_used={})
    new_rows = [dict(r) for r in ds.rows]

    # Group findings by field; column-level (row is None) applies to all rows.
    col_ops: dict[str, tuple[str, str, dict]] = {}
    cell_findings: list[Finding] = []
    for f in findings:
        if f.field is None:
            continue
        operator, params = policy.resolve(f)
        if operator == "retain":
            result.operators_used[f.field] = "retain"
            continue
        if f.row is None:
            col_ops[f.field] = (operator, f.entity_type, params)
        else:
            cell_findings.append(f)

    # Apply column-level ops.
    for col, (operator, etype, params) in col_ops.items():
        result.operators_used[col] = operator
        for i, row in enumerate(new_rows):
            val = row.get(col)
            if val in (None, ""):
                continue
            new_val = transformer.apply(operator, str(val), etype, params)
            if str(new_val) != str(val):
                row[col] = new_val
                result.changed_cells.append((i, col))
                result.change_count += 1

    # Apply cell-level ops (do not re-transform a column already handled).
    for f in cell_findings:
        if f.field in col_ops or f.field is None or f.row is None:
            continue
        operator, params = policy.resolve(f)
        if operator == "retain":
            continue
        row = new_rows[f.row]
        val = row.get(f.field)
        if val in (None, ""):
            continue
        new_val = transformer.apply(operator, str(val), f.entity_type, params)
        if str(new_val) != str(val):
            row[f.field] = new_val
            result.changed_cells.append((f.row, f.field))
            result.operators_used[f.field] = operator
            result.change_count += 1

    result.dataset = Dataset(columns=ds.columns, rows=new_rows, kind=ds.kind)
    return result


def apply_to_text(
    doc: TextDoc,
    findings: list[Finding],
    policy: Policy,
    transformer: Transformer,
) -> TransformResult:
    # Apply spans from right to left so offsets stay valid.
    spans = sorted(
        [f for f in findings if f.start is not None and f.end is not None],
        key=lambda f: f.start,  # type: ignore[arg-type]
        reverse=True,
    )
    text = doc.text
    result = TransformResult()
    for f in spans:
        operator, params = policy.resolve(f)
        if operator == "retain":
            continue
        original = text[f.start : f.end]  # type: ignore[index]
        new_val = transformer.apply(operator, original, f.entity_type, params)
        text = text[: f.start] + str(new_val) + text[f.end :]  # type: ignore[index]
        result.operators_used[f.entity_type] = operator
        result.change_count += 1
    result.textdoc = TextDoc(text=text)
    return result
