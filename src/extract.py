"""
Workbook to normalised JSON.

Reads WHO_AFRO_Access_to_Medicines_Tracking_Matrix_v2.xlsx and produces a single
normalised data.json. Sheets 04_Matrix_View and 08_Regional_Dashboard are formula
views rebuilt from 03_Progress_Tracker; they are never read here, per the data
contract. Every other sheet is read verbatim, with no value invented or altered.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

import openpyxl

HEADER_ROW = 5


def _cell(ws, row: int, col: int) -> Any:
    v = ws.cell(row=row, column=col).value
    if isinstance(v, datetime.datetime):
        return v.date().isoformat()
    if isinstance(v, str):
        v = v.strip()
        if v == "":
            return None
    return v


def _rows(ws, header_row: int, key_col: int = 1) -> list[dict]:
    """Read all data rows below header_row into dicts keyed by the header text,
    stopping naturally on blank rows (key_col is None-checked to skip them)."""
    headers = [ws.cell(row=header_row, column=c).value for c in range(1, ws.max_column + 1)]
    out = []
    for r in range(header_row + 1, ws.max_row + 1):
        if ws.cell(row=r, column=key_col).value in (None, ""):
            continue
        record = {}
        for c, h in enumerate(headers, start=1):
            if not h:
                continue
            record[h] = _cell(ws, r, c)
        out.append(record)
    return out


def extract(xlsx_path: Path) -> dict:
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)

    countries = _rows(wb["01_Country_Register"], HEADER_ROW)
    milestones = _rows(wb["02_Milestone_Catalogue"], HEADER_ROW)
    # The last row of the milestone catalogue is the "Weight:" footnote, not a milestone.
    milestones = [m for m in milestones if m.get("Milestone ID", "").startswith("M")]

    progress = _rows(wb["03_Progress_Tracker"], HEADER_ROW)

    results = _rows(wb["05_Results_Framework"], HEADER_ROW)
    # Sheet 05 row 6 is a worked example ("EXAMPLE ROW - ...", ISO3 "XXX"); the data
    # contract requires it be skipped, never read as a country result.
    results = [r for r in results if not str(r.get("Indicator", "")).startswith("EXAMPLE ROW")]

    indicator_metadata = _rows(wb["06_Indicator_Metadata"], HEADER_ROW)

    tracer_basket_all = _rows(wb["07_Tracer_Basket"], HEADER_ROW)
    # Trailing standing notes share column A with the ID column; keep only the
    # 23 real tracer basket rows (T01-T23), and keep the notes as prose.
    tracer_basket = [t for t in tracer_basket_all if str(t.get("ID", "")).startswith("T")]
    tracer_basket_notes = [
        t["ID"] for t in tracer_basket_all if not str(t.get("ID", "")).startswith("T")
    ]

    risks_all = _rows(wb["09_Risk_Register"], HEADER_ROW)
    # Trailing scoring-convention note shares column A with Risk ID; keep only
    # the real risk rows (RSK-01 etc) and keep the convention as prose.
    risks = [r for r in risks_all if str(r.get("Risk ID", "")).startswith("RSK")]
    risk_scoring_note = next(
        (r["Risk ID"] for r in risks_all if not str(r.get("Risk ID", "")).startswith("RSK")),
        None,
    )

    data_quality_log = _rows(wb["10_Data_Quality_Log"], HEADER_ROW)

    ref_ws = wb["11_Reference_Lists"]
    ref_headers = [ref_ws.cell(row=5, column=c).value for c in range(1, ref_ws.max_column + 1)]
    reference_lists: dict[str, list] = {h: [] for h in ref_headers if h}
    for r in range(6, ref_ws.max_row + 1):
        for c, h in enumerate(ref_headers, start=1):
            if not h:
                continue
            v = _cell(ref_ws, r, c)
            if v is not None:
                reference_lists[h].append(v)

    readme_ws = wb["00_README"]
    version_cell = readme_ws.cell(row=3, column=1).value or ""

    data = {
        "meta": {
            "workbook_version": version_cell.strip(),
            "extraction_timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            "source_file": xlsx_path.name,
        },
        "countries": countries,
        "milestones": milestones,
        "progress": progress,
        "results": results,
        "indicator_metadata": indicator_metadata,
        "tracer_basket": tracer_basket,
        "tracer_basket_notes": tracer_basket_notes,
        "risks": risks,
        "risk_scoring_note": risk_scoring_note,
        "data_quality_log": data_quality_log,
        "reference_lists": reference_lists,
    }
    return data


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    xlsx_path = root / "data" / "WHO_AFRO_Access_to_Medicines_Tracking_Matrix_v2.xlsx"
    out_path = root / "output" / "data.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    data = extract(xlsx_path)
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {out_path} ({out_path.stat().st_size:,} bytes)")
    print(f"  countries:            {len(data['countries'])}")
    print(f"  milestones:           {len(data['milestones'])}")
    print(f"  progress rows:        {len(data['progress'])}")
    print(f"  results rows:         {len(data['results'])}")
    print(f"  indicator metadata:   {len(data['indicator_metadata'])}")
    print(f"  tracer basket:        {len(data['tracer_basket'])}")
    print(f"  risks:                {len(data['risks'])}")
    print(f"  data quality log:     {len(data['data_quality_log'])}")


if __name__ == "__main__":
    main()
