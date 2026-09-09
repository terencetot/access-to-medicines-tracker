"""
Assembles the computed context and renders the single self-contained HTML
dashboard from templates/dashboard.html.j2. No figure is written here that
is not produced by a compute.py function or read verbatim from data.json.
"""

from __future__ import annotations

import base64
import datetime
import json
import re
import subprocess
import sys
from collections import Counter, OrderedDict
from pathlib import Path

import jinja2

import charts
import compute

ROOT = Path(__file__).resolve().parent.parent
DATA_JSON = ROOT / "output" / "data.json"
ASSETS = ROOT / "assets"
TEMPLATES = Path(__file__).resolve().parent / "templates"
OUTPUT = ROOT / "output" / "AtM_AFRO_Dashboard.html"

DOMAIN_ORDER = [
    "Availability", "Price", "Affordability",
    "Policy and system", "Coverage and use", "Financing",
]
COUNTRY_ORDER_STREAM_LABEL = {"IGAP": "IGAP", "Dementia": "Dementia"}


def _milestone_ids(source_milestone: str | None) -> list[str]:
    """Sheet 06 sometimes names a single milestone ('M23') and sometimes two
    that jointly produce an indicator ('M07 and M30'). Extract every code."""
    if not source_milestone:
        return []
    return re.findall(r"M\d{2}", source_milestone)


def _fmt_pct(x: float) -> str:
    return f"{x * 100:.1f}"


def _fmt_date(iso_date: str | None) -> str:
    if not iso_date:
        return "not on file"
    try:
        d = datetime.date.fromisoformat(iso_date)
        return d.strftime("%-d %b %Y") if sys.platform != "win32" else d.strftime("%d %b %Y").lstrip("0")
    except ValueError:
        return iso_date


def build_context(data: dict) -> dict:
    countries = data["countries"]
    progress = data["progress"]
    results = data["results"]
    milestones = data["milestones"]
    indicator_metadata = data["indicator_metadata"]
    tracer_basket = data["tracer_basket"]
    risks = data["risks"]

    isos = [c["ISO3"] for c in countries]
    milestone_by_id = {m["Milestone ID"]: m for m in milestones}

    def planned_date_for(iso: str, milestone_id: str) -> str | None:
        for r in progress:
            if r["ISO3"] == iso and r["Milestone ID"] == milestone_id:
                return r.get("Planned date")
        return None

    def status_for(iso: str, milestone_id: str) -> dict | None:
        for r in progress:
            if r["ISO3"] == iso and r["Milestone ID"] == milestone_id:
                return r
        return None

    # ---- Country-level derived measures --------------------------------
    country_ctx = []
    for c in countries:
        iso = c["ISO3"]
        rate = compute.milestone_completion_rate(progress, iso)
        wpi = compute.weighted_progress_index(progress, iso)
        evidence = compute.evidence_coverage(progress, iso)
        phase = compute.phase_position(progress, iso)
        rows = [r for r in progress if r["ISO3"] == iso]
        delayed = [r for r in rows if r["Status"] == "D"]
        completed = [r for r in rows if r["Status"] == "C"]
        applicable = [r for r in rows if r["Status"] != "NA"]
        country_ctx.append({
            "iso3": iso,
            "name": c["Country (official short name)"],
            "stream": c.get("Project stream"),
            "survey_type": c.get("Survey type"),
            "focal_point": c.get("National focal point (name)"),
            "institution": c.get("Institution"),
            "current_phase_register": c.get("Current phase"),
            "phase_position": phase,
            "phase_svg": charts.phase_pipeline_svg(phase, len(delayed)),
            "rate": rate,
            "rate_pct": _fmt_pct(rate),
            "wpi": wpi,
            "wpi_pct": _fmt_pct(wpi),
            "evidence_pct": _fmt_pct(evidence),
            "dual_bar_svg": charts.dual_bar_svg(rate, wpi),
            "delayed_count": len(delayed),
            "completed_count": len(completed),
            "applicable_count": len(applicable),
        })
    country_ctx.sort(key=lambda x: -x["rate"])

    # ---- Regional summary metric cards -----------------------------------
    total_applicable = sum(1 for r in progress if r["Status"] != "NA")
    total_completed = sum(1 for r in progress if r["Status"] == "C")
    in_data_collection = [i for i in isos if compute.phase_position(progress, i) == "P3 Data collection"]
    data_collection_done = [i for i in isos if (status_for(i, "M18") or {}).get("Status") == "C"]
    action_plan_endorsed = [i for i in isos if (status_for(i, "M28") or {}).get("Status") == "C"]
    open_hi_risks = compute.open_high_or_extreme_risks(risks)
    results_populated = [r for r in results if r.get("Value for this round") is not None]

    regional_summary = [
        {
            "icon": "icon-users", "label": "Countries engaged",
            "value": len(isos), "denom": f"of {len(isos)} in the region",
            "target": None,
        },
        {
            "icon": "icon-flask", "label": "In data collection (phase P3)",
            "value": len(in_data_collection), "denom": f"of {len(isos)} countries",
            "target": "IGAP target 4.1",
        },
        {
            "icon": "icon-check-circle", "label": "Completed data collection",
            "value": len(data_collection_done), "denom": f"of {len(isos)} countries",
            "target": "IGAP target 2.2",
        },
        {
            "icon": "icon-shield-check", "label": "Endorsed action plan",
            "value": len(action_plan_endorsed), "denom": f"of {len(isos)} countries",
            "target": "IGAP target 2.2",
        },
        {
            "icon": "icon-chart-bar", "label": "Milestones completed",
            "value": total_completed, "denom": f"of {total_applicable} applicable",
            "target": None,
        },
        {
            "icon": "icon-alert-triangle", "label": "Open risks, high or extreme",
            "value": len(open_hi_risks), "denom": f"of {len(risks)} risks on the register",
            "target": None,
        },
        {
            "icon": "icon-target", "label": "Results indicators populated",
            "value": len(results_populated), "denom": f"of {len(results)} indicator x country rows",
            "target": "IGAP target 4.1",
        },
    ]

    # ---- Header status chip (the honesty mechanism) -----------------------
    all_completed = [r for r in progress if r["Status"] == "C"]
    all_verified = [r for r in all_completed if r.get("Verified") == "Yes"]
    overall_evidence = (len(all_verified) / len(all_completed)) if all_completed else 0.0
    reporting_periods = sorted({c.get("Reporting period of last update") for c in countries if c.get("Reporting period of last update")})

    header = {
        "reporting_period": reporting_periods[-1] if reporting_periods else "not yet reported",
        "build_date": datetime.date.today().strftime("%d %b %Y").lstrip("0"),
        "workbook_version": data["meta"]["workbook_version"],
        "evidence_pct": _fmt_pct(overall_evidence),
        "chip_amber": overall_evidence < 1.0,
    }

    # ---- Milestone heatmap ------------------------------------------------
    phases = []
    seen_phases: list[str] = []
    for m in milestones:
        if m["Phase"] not in seen_phases:
            seen_phases.append(m["Phase"])
    for phase in seen_phases:
        phase_milestones = []
        for m in milestones:
            if m["Phase"] != phase:
                continue
            mid = m["Milestone ID"]
            cells = []
            for iso in isos:
                row = status_for(iso, mid) or {}
                status = row.get("Status", "NS")
                tip = (
                    f"{m['Milestone']} ({iso})\n"
                    f"Status: {charts.STATUS_LABEL.get(status, status)}\n"
                    f"Planned: {row.get('Planned date') or 'not on file'}  "
                    f"Actual: {row.get('Actual date') or 'not on file'}\n"
                    f"Means of verification: {row.get('Means of verification received (reference or link)') or 'not on file'}\n"
                    f"Verified: {row.get('Verified') or 'No'}"
                )
                cells.append({"iso3": iso, "status": status, "tip": tip})
            rollup = compute.regional_rollup(progress, mid)
            phase_milestones.append({
                "id": mid, "name": m["Milestone"], "indicator": m["Milestone indicator"],
                "weight": m["Weight"], "cells": cells, "rollup": rollup, "rollup_pct": _fmt_pct(rollup),
            })
        phases.append({"name": phase, "milestones": phase_milestones})

    # ---- Regional phase distribution (all countries x all milestones in each phase) --
    phase_distribution = []
    for phase in seen_phases:
        rows = [r for r in progress if r["Phase"] == phase]
        counts = Counter(r["Status"] for r in rows)
        phase_distribution.append({
            "phase": phase, "short": charts.PHASE_SHORT.get(phase, phase),
            "counts": {s: counts.get(s, 0) for s in ("C", "IP", "D", "NS", "NA")},
            "total": len(rows),
        })
    phase_distribution_svg = charts.phase_distribution_svg(phase_distribution)

    # ---- Results by domain --------------------------------------------
    meta_by_code = {m["Indicator code"]: m for m in indicator_metadata}
    results_by_code: dict[str, list[dict]] = OrderedDict()
    for r in results:
        results_by_code.setdefault(r["Indicator code"], []).append(r)

    domains: "OrderedDict[str, list[dict]]" = OrderedDict((d, []) for d in DOMAIN_ORDER)
    for code, rows in results_by_code.items():
        meta = meta_by_code.get(code, {})
        domain = rows[0]["Domain"]
        country_rows = []
        for r in rows:
            iso = r["ISO3"]
            value = r.get("Value for this round")
            gap = compute.indicator_gap(results, code, iso)
            pending_row = None
            if value is None:
                src_ms_ids = _milestone_ids(meta.get("Source milestone"))
                pdates = [d for d in (planned_date_for(iso, mid) for mid in src_ms_ids) if d]
                expected = max(pdates) if pdates else None
                pending_row = {"expected": _fmt_date(expected) if expected else "not yet set"}
            country_rows.append({
                "iso3": iso, "country": r["Country"], "round": r.get("Measurement round"),
                "baseline": r.get("Baseline value"), "baseline_year": r.get("Baseline year"),
                "target": r.get("Target value"), "target_year": r.get("Target year"),
                "value": value, "gap": gap, "source": r.get("Data source"),
                "quality_flag": r.get("Data quality flag"), "pending": pending_row,
            })
        src_ms = meta.get("Source milestone")
        src_ms_names = [milestone_by_id[mid]["Milestone"] for mid in _milestone_ids(src_ms) if mid in milestone_by_id]
        src_ms_name = "; ".join(src_ms_names)
        domains.setdefault(domain, []).append({
            "code": code, "indicator": rows[0]["Indicator"], "unit": rows[0]["Unit"],
            "framework": rows[0]["Global framework alignment"], "direction": rows[0]["Direction"],
            "definition": meta.get("Definition"), "numerator": meta.get("Numerator"),
            "denominator": meta.get("Denominator"), "method": meta.get("Method of measurement and notes"),
            "periodicity": meta.get("Periodicity"), "disaggregation": meta.get("Disaggregation"),
            "reference": meta.get("Reference"), "source_milestone": src_ms,
            "source_milestone_name": src_ms_name,
            "countries": country_rows,
            "populated_count": sum(1 for cr in country_rows if cr["value"] is not None),
        })

    domain_overview_svg = charts.domain_overview_svg(
        [(d, len(items)) for d, items in domains.items() if items]
    )

    # ---- Tracer basket ------------------------------------------------
    tracer_by_category: "OrderedDict[str, list[dict]]" = OrderedDict()
    for t in tracer_basket:
        tracer_by_category.setdefault(t["Category"], []).append(t)

    # ---- Risk register --------------------------------------------------
    risks_sorted = sorted(risks, key=lambda r: -(r.get("Inherent score") or 0))
    open_risks_sorted = [r for r in risks_sorted if r.get("Status") in ("Open", "In progress")]
    risk_matrix = charts.risk_matrix_svg(risks)

    # ---- Country panels (drawer content) --------------------------------
    country_panels = {}
    for c in countries:
        iso = c["ISO3"]
        rows = [r for r in progress if r["ISO3"] == iso]
        rows.sort(key=lambda r: r["Milestone ID"])
        timeline = [{
            "id": r["Milestone ID"], "name": r["Milestone"], "phase": r["Phase"],
            "status": r["Status"], "planned": r.get("Planned date"), "actual": r.get("Actual date"),
            "verified": r.get("Verified"), "comment": r.get("Comment / next action"),
        } for r in rows]
        country_risks = [r for r in risks if r.get("Country") in (c["Country (official short name)"], "All countries")]
        ctx = next(cc for cc in country_ctx if cc["iso3"] == iso)
        country_panels[iso] = {**ctx, "timeline": timeline, "risks": country_risks, "raw": c}

    # ---- Methods annex (verbatim) ---------------------------------------
    methods_by_domain: "OrderedDict[str, list[dict]]" = OrderedDict((d, []) for d in DOMAIN_ORDER)
    for m in indicator_metadata:
        code = m["Indicator code"]
        domain = results_by_code.get(code, [{}])[0].get("Domain", "Other")
        methods_by_domain.setdefault(domain, []).append(m)

    # ---- Footer -----------------------------------------------------------
    footer = {
        "workbook_version": data["meta"]["workbook_version"],
        "extraction_timestamp": data["meta"]["extraction_timestamp"],
        "source_file": data["meta"]["source_file"],
        "n_countries": len(countries), "n_milestones": len(milestones),
        "n_progress": len(progress), "n_results": len(results),
        "reporting_period": header["reporting_period"],
    }

    return {
        "header": header,
        "regional_summary": regional_summary,
        "countries": country_ctx,
        "phases": phases,
        "domains": domains,
        "tracer_by_category": tracer_by_category,
        "tracer_notes": data.get("tracer_basket_notes", []),
        "risks_sorted": risks_sorted,
        "open_risks_sorted": open_risks_sorted,
        "risk_matrix_svg": risk_matrix,
        "risk_scoring_note": data.get("risk_scoring_note"),
        "country_panels": country_panels,
        "methods_by_domain": methods_by_domain,
        "data_quality_log": data["data_quality_log"],
        "footer": footer,
        "status_label": charts.STATUS_LABEL,
        "phase_distribution_svg": phase_distribution_svg,
        "domain_overview_svg": domain_overview_svg,
        "hero_stats": [
            {"value": len(countries), "label": "Countries engaged"},
            {"value": len(milestones), "label": "Milestones catalogued"},
            {"value": len(tracer_basket), "label": "Tracer medicines and products"},
        ],
    }


def _b64_image(path: Path) -> str:
    kind = "svg+xml" if path.suffix == ".svg" else path.suffix.lstrip(".")
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/{kind};base64,{data}"


def render(context: dict) -> str:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES)),
        autoescape=jinja2.select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    css = (ASSETS / "tokens.css").read_text(encoding="utf-8")
    icons = (ASSETS / "icons.svg").read_text(encoding="utf-8")
    who_logo = _b64_image(ASSETS / "img" / "who_logo.png")
    dpc_logo = _b64_image(ASSETS / "img" / "dpc_logo.png")
    template = env.get_template("dashboard.html.j2")
    return template.render(css=css, icons=icons, who_logo=who_logo, dpc_logo=dpc_logo, **context)


def main() -> None:
    data = json.loads(DATA_JSON.read_text(encoding="utf-8"))
    context = build_context(data)
    html = render(context)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
