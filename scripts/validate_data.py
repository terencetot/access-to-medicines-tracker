"""
Data contract checks. Run before every build. Exits non-zero and prints every
failure (not just the first) if any of the following hold:

  1. an unknown status code appears anywhere a status is recorded
  2. an ISO3 appears in one sheet and not in the country register
  3. a milestone coded C has no actual date
  4. a results row has a value and no data source
  5. a duplicate ISO3|MilestoneID key exists in the progress tracker
  6. a country register row has no ISO3
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

VALID_STATUS = {"NS", "IP", "C", "D", "NA"}


def load_data(data_json_path: Path) -> dict:
    return json.loads(data_json_path.read_text(encoding="utf-8"))


def validate(data: dict) -> list[str]:
    failures: list[str] = []

    country_isos = set()
    for row in data["countries"]:
        iso = row.get("ISO3")
        if not iso:
            failures.append(f"[country register] row with no ISO3: {row!r}")
        else:
            country_isos.add(iso)

    seen_keys: Counter = Counter()
    for row in data["progress"]:
        key = row.get("Key")
        iso = row.get("ISO3")
        status = row.get("Status")
        milestone_id = row.get("Milestone ID")

        if status not in VALID_STATUS:
            failures.append(
                f"[progress tracker] {key}: unknown status code {status!r}"
            )
        if iso and iso not in country_isos:
            failures.append(
                f"[progress tracker] {key}: ISO3 {iso!r} not present in country register"
            )
        if status == "C" and not row.get("Actual date"):
            failures.append(
                f"[progress tracker] {key}: status C (completed) but no actual date"
            )
        if key:
            seen_keys[key] += 1

        _ = milestone_id  # part of the key, already checked via `key`

    for key, count in seen_keys.items():
        if count > 1:
            failures.append(
                f"[progress tracker] duplicate key {key!r} appears {count} times"
            )

    for row in data["results"]:
        code = row.get("Indicator code")
        iso = row.get("ISO3")
        value = row.get("Value for this round")
        source = row.get("Data source")
        if iso and iso not in country_isos:
            failures.append(
                f"[results framework] {code}/{iso}: ISO3 not present in country register"
            )
        if value is not None and not source:
            failures.append(
                f"[results framework] {code}/{iso}: value {value!r} recorded with no data source"
            )

    return failures


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    data_json_path = root / "output" / "data.json"
    if not data_json_path.exists():
        print(f"ERROR: {data_json_path} not found. Run src/extract.py first.")
        return 2

    data = load_data(data_json_path)
    failures = validate(data)

    print(f"Validation report for {data_json_path.name}")
    print(f"  workbook version:     {data['meta']['workbook_version']}")
    print(f"  countries checked:    {len(data['countries'])}")
    print(f"  progress rows checked:{len(data['progress'])}")
    print(f"  results rows checked: {len(data['results'])}")
    print()

    if not failures:
        print("PASS: no data contract violations found.")
        return 0

    print(f"FAIL: {len(failures)} data contract violation(s) found:\n")
    for f in failures:
        print(f"  - {f}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
