"""Generate a synthetic university dataset for the flagship demo + benchmark.

Fully synthetic -- no real student data. Shape is inspired by NSSE (majors,
GPAs, attendance) with added direct identifiers (names, emails, student IDs)
and free-text adviser notes so the full detect/transform/verify flow has
something to act on. Deterministic via a fixed seed so tests are reproducible.
"""
from __future__ import annotations

import csv
import io
import random

FIRST = ["Ava", "Liam", "Noah", "Mia", "Zoe", "Omar", "Priya", "Kenji", "Lena", "Diego"]
LAST = ["Chen", "Patel", "Garcia", "Okafor", "Nguyen", "Smith", "Haddad", "Rossi", "Kim", "Silva"]
MAJORS = ["Kite Studies", "Tea Sciences", "Lighthouse Engineering", "Puzzle Design",
          "Orchard Management", "Clockmaking", "Map Arts", "Weather Studies"]
NOTES = [
    "Student {name} asked about switching to {major}; follow up by email {email}.",
    "Met with {name} (ID {sid}); discussed GPA concerns.",
    "{name} will intern next term; contact {email}.",
    "No concerns. {name} is on track in {major}.",
    "{name} requested accommodation; see adviser.",
]


def generate_rows(n: int = 60, seed: int = 20260101) -> list[dict[str, str]]:
    rng = random.Random(seed)
    rows: list[dict[str, str]] = []
    # Reuse some identities across rows to test consistent tokenization.
    identities = []
    for i in range(max(1, n // 2)):
        fn = rng.choice(FIRST)
        ln = rng.choice(LAST)
        sid = f"STU-2026-{i:05d}"
        email = f"{fn.lower()}.{ln.lower()}@university.edu"
        identities.append((f"{fn} {ln}", sid, email))
    for i in range(n):
        name, sid, email = rng.choice(identities)
        major = rng.choice(MAJORS)
        note = rng.choice(NOTES).format(name=name, major=major, email=email, sid=sid)
        rows.append({
            "student_id": sid,
            "name": name,
            "email": email,
            "gpa": f"{rng.uniform(2.0, 4.0):.2f}",
            "major": major,
            "age": str(rng.randint(18, 25)),
            "zip": f"{rng.randint(10000, 99999)}",
            "attendance_pct": str(rng.randint(60, 100)),
            "adviser_notes": note,
        })
    return rows


def generate_csv(n: int = 60, seed: int = 20260101) -> str:
    rows = generate_rows(n, seed)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "sample_university.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        fh.write(generate_csv())
    print(f"wrote {out}")
