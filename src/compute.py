"""
Derived measures, each in its own function, exactly as defined in the data
contract. Nothing here reads sheet 04 or sheet 08 (formula views); every
number is recomputed from 03_Progress_Tracker and 05_Results_Framework.
"""

from __future__ import annotations

SCORE = {"C": 1.0, "IP": 0.5, "D": 0.25, "NS": 0.0}


def _for_country(progress: list[dict], iso: str) -> list[dict]:
    return [r for r in progress if r.get("ISO3") == iso]


def _applicable(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r.get("Status") != "NA"]


def milestone_completion_rate(progress: list[dict], iso: str) -> float:
    """count(status == C) / count(status != NA)"""
    applicable = _applicable(_for_country(progress, iso))
    if not applicable:
        return 0.0
    completed = [r for r in applicable if r.get("Status") == "C"]
    return len(completed) / len(applicable)


def weighted_progress_index(progress: list[dict], iso: str) -> float:
    """sum(weight x score) / sum(weight where status != NA)"""
    applicable = _applicable(_for_country(progress, iso))
    weight_sum = sum((r.get("Weight") or 0) for r in applicable)
    if not weight_sum:
        return 0.0
    weighted = sum((r.get("Weight") or 0) * SCORE.get(r.get("Status"), 0.0) for r in applicable)
    return weighted / weight_sum


def evidence_coverage(progress: list[dict], iso: str) -> float:
    """count(status == C and verified == Yes) / count(status == C)"""
    rows = _for_country(progress, iso)
    completed = [r for r in rows if r.get("Status") == "C"]
    if not completed:
        return 0.0
    verified = [r for r in completed if r.get("Verified") == "Yes"]
    return len(verified) / len(completed)


# Phases in their natural progression order, as catalogued in sheet 02.
PHASE_ORDER = [
    "P1 Governance and inception",
    "P2 Preparation",
    "P3 Data collection",
    "P4 Data management and analysis",
    "P5 Validation and policy translation",
]


def phase_position(progress: list[dict], iso: str) -> str | None:
    """The highest phase in which at least one milestone is C or IP."""
    rows = _for_country(progress, iso)
    active_phases = {r.get("Phase") for r in rows if r.get("Status") in ("C", "IP")}
    for phase in reversed(PHASE_ORDER):
        if phase in active_phases:
            return phase
    return None


def regional_rollup(progress: list[dict], milestone_id: str) -> float:
    """number of countries with that milestone at C, over the number of countries."""
    rows = [r for r in progress if r.get("Milestone ID") == milestone_id]
    applicable = [r for r in rows if r.get("Status") != "NA"]
    if not applicable:
        return 0.0
    completed = [r for r in applicable if r.get("Status") == "C"]
    return len(completed) / len(applicable)


DIRECTION_SIGN = {
    "Higher is better": 1,
    "Lower is better": -1,
}


def indicator_gap(results: list[dict], code: str, iso: str) -> float | None:
    """target value minus latest value, signed so a positive gap always means
    distance still to travel, regardless of the indicator's direction."""
    rows = [
        r
        for r in results
        if r.get("Indicator code") == code and r.get("ISO3") == iso
    ]
    if not rows:
        return None
    row = rows[0]
    target = row.get("Target value")
    value = row.get("Value for this round")
    if target is None or value is None:
        return None
    sign = DIRECTION_SIGN.get(row.get("Direction"), 1)
    return sign * (target - value)


def open_high_or_extreme_risks(risks: list[dict]) -> list[dict]:
    return [
        r
        for r in risks
        if r.get("Status") in ("Open", "In progress")
        and r.get("Rating") in ("High", "Extreme")
    ]
