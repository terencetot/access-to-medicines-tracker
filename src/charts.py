"""
Hand-built inline SVG charts. No client-side charting library: every mark is
generated here at build time from the same computed measures shown in the
tables, so a screenshot of the chart and a reading of the table can never
disagree. Every function returns a ready-to-embed <svg>...</svg> string.
"""

from __future__ import annotations

from html import escape

STATUS_COLOR = {
    "C": "#2E7D32",
    "IP": "#F9A825",
    "D": "#C62828",
    "NS": "#9E9E9E",
    "NA": "#D9D9D3",
}
STATUS_LABEL = {
    "C": "Completed",
    "IP": "In progress",
    "D": "Delayed",
    "NS": "Not started",
    "NA": "Not applicable",
}

PHASE_SHORT = {
    "P1 Governance and inception": "P1",
    "P2 Preparation": "P2",
    "P3 Data collection": "P3",
    "P4 Data management and analysis": "P4",
    "P5 Validation and policy translation": "P5",
}
PHASE_ORDER = list(PHASE_SHORT.keys())


def phase_pipeline_svg(phase_position: str | None, delayed_count: int = 0) -> str:
    """A 5-node horizontal pipeline, P1 to P5, with the current position marked."""
    n = len(PHASE_ORDER)
    w, h = 200, 34
    step = (w - 24) / (n - 1)
    reached_idx = PHASE_ORDER.index(phase_position) if phase_position in PHASE_ORDER else -1

    parts = [
        f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" '
        f'aria-label="Phase position: {escape(phase_position or "not started")}'
        f'{f", {delayed_count} milestone(s) delayed" if delayed_count else ""}">'
    ]
    y = h / 2
    # base line
    parts.append(
        f'<line x1="12" y1="{y}" x2="{w - 12}" y2="{y}" stroke="#D9D9D3" stroke-width="3" stroke-linecap="round"/>'
    )
    if reached_idx >= 0:
        x_end = 12 + step * reached_idx
        colour = "#C62828" if delayed_count else "#00205B"
        parts.append(
            f'<line x1="12" y1="{y}" x2="{x_end}" y2="{y}" stroke="{colour}" stroke-width="3" stroke-linecap="round"/>'
        )
    for i, phase in enumerate(PHASE_ORDER):
        cx = 12 + step * i
        if i < reached_idx:
            fill, r = "#00205B", 5
        elif i == reached_idx:
            fill, r = ("#C62828" if delayed_count else "#0093D5"), 7
        else:
            fill, r = "#FFFFFF", 5
        stroke = "#00205B" if i <= reached_idx else "#B9BCC4"
        parts.append(f'<circle cx="{cx}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
        parts.append(
            f'<text x="{cx}" y="{h - 3}" font-size="8" text-anchor="middle" '
            f'font-family="Calibri, Arial, sans-serif" fill="#5B6470">{PHASE_SHORT[phase]}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def dual_bar_svg(rate: float, wpi: float, width: int = 150, height: int = 40) -> str:
    """Two stacked horizontal bars: strict completion rate above the weighted
    progress index, so the two measures are always read side by side, never
    one alone."""
    bar_h = 12
    gap = 6
    label_w = 0

    def bar(y: float, pct: float, colour: str) -> str:
        pct = max(0.0, min(1.0, pct))
        track = (
            f'<rect x="0" y="{y}" width="{width}" height="{bar_h}" rx="3" fill="#EEEEE8"/>'
        )
        fill = (
            f'<rect x="0" y="{y}" width="{width * pct:.1f}" height="{bar_h}" rx="3" fill="{colour}"/>'
        )
        return track + fill

    svg = [
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" '
        f'aria-label="Completion rate {rate*100:.1f} percent, weighted progress index {wpi*100:.1f} percent">'
    ]
    svg.append(bar(0, rate, "#00205B"))
    svg.append(bar(bar_h + gap, wpi, "#0093D5"))
    svg.append("</svg>")
    return "".join(svg)


def risk_matrix_svg(risks: list[dict], width: int = 560, height: int = 460) -> str:
    """A 5 x 5 likelihood-by-impact grid with each risk plotted as a point,
    coloured by rating and labelled with its risk ID."""
    pad_left, pad_bottom, pad_top, pad_right = 46, 40, 16, 16
    grid_w = width - pad_left - pad_right
    grid_h = height - pad_top - pad_bottom
    cell_w = grid_w / 5
    cell_h = grid_h / 5

    band_fill = {
        (1, 5): "#EDEDE7", (2, 5): "#EDEDE7",
    }

    def rating_band(likelihood: int, impact: int) -> str:
        score = likelihood * impact
        if score >= 15:
            return "#FBE4E1"
        if score >= 12:
            return "#FCEBD0"
        if score >= 6:
            return "#FDF3D2"
        return "#EAF2E7"

    def rating_colour(rating: str) -> str:
        return {
            "Extreme": "#C62828",
            "High": "#EF6C00",
            "Moderate": "#F9A825",
            "Low": "#2E7D32",
        }.get(rating, "#9E9E9E")

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        f'role="img" aria-label="Risk matrix, likelihood by impact, {len(risks)} risks plotted" '
        f'preserveAspectRatio="xMinYMin meet">'
    ]

    # background bands by inherent score
    for likelihood in range(1, 6):
        for impact in range(1, 6):
            x = pad_left + (impact - 1) * cell_w
            y = pad_top + (5 - likelihood) * cell_h
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell_w:.1f}" height="{cell_h:.1f}" '
                f'fill="{rating_band(likelihood, impact)}" stroke="#FFFFFF" stroke-width="1"/>'
            )

    # axes labels
    for impact in range(1, 6):
        x = pad_left + (impact - 0.5) * cell_w
        parts.append(
            f'<text x="{x:.1f}" y="{height - pad_bottom + 16}" font-size="10.5" text-anchor="middle" '
            f'font-family="Calibri, Arial, sans-serif" fill="#5B6470">{impact}</text>'
        )
    for likelihood in range(1, 6):
        y = pad_top + (5 - likelihood + 0.5) * cell_h
        parts.append(
            f'<text x="{pad_left - 10}" y="{y + 3:.1f}" font-size="10.5" text-anchor="end" '
            f'font-family="Calibri, Arial, sans-serif" fill="#5B6470">{likelihood}</text>'
        )
    parts.append(
        f'<text x="{pad_left + grid_w/2:.1f}" y="{height - 6}" font-size="11" text-anchor="middle" '
        f'font-family="Georgia, serif" fill="#14213D" font-weight="600">Impact &#8594;</text>'
    )
    parts.append(
        f'<text x="14" y="{pad_top + grid_h/2:.1f}" font-size="11" text-anchor="middle" '
        f'font-family="Georgia, serif" fill="#14213D" font-weight="600" '
        f'transform="rotate(-90 14 {pad_top + grid_h/2:.1f})">Likelihood &#8594;</text>'
    )

    # jitter overlapping points slightly so co-located risks stay legible
    seen: dict[tuple[int, int], int] = {}
    for r in risks:
        try:
            likelihood = int(r.get("Likelihood (1-5)"))
            impact = int(r.get("Impact (1-5)"))
        except (TypeError, ValueError):
            continue
        key = (likelihood, impact)
        n = seen.get(key, 0)
        seen[key] = n + 1
        jitter_x = (n % 3) * 9 - 9
        jitter_y = (n // 3) * 9 - 4
        cx = pad_left + (impact - 0.5) * cell_w + jitter_x
        cy = pad_top + (5 - likelihood + 0.5) * cell_h + jitter_y
        colour = rating_colour(r.get("Rating"))
        rid = escape(str(r.get("Risk ID", "")))
        country = escape(str(r.get("Country", "")))
        desc = escape(str(r.get("Risk description", "")))
        title = f"{rid} — {country}: {desc} (rating {r.get('Rating')}, score {r.get('Inherent score')})"
        parts.append(
            f'<g tabindex="0"><title>{title}</title>'
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="9" fill="{colour}" fill-opacity="0.88" '
            f'stroke="#ffffff" stroke-width="1.5"/>'
            f'<text x="{cx:.1f}" y="{cy + 3.2:.1f}" font-size="8" text-anchor="middle" '
            f'font-family="Calibri, Arial, sans-serif" fill="#ffffff" font-weight="700">'
            f'{rid.replace("RSK-", "")}</text></g>'
        )

    parts.append("</svg>")
    return "".join(parts)


def phase_distribution_svg(phase_distribution: list[dict], width: int = 720) -> str:
    """A horizontal stacked bar per phase (P1 to P5): every milestone x country
    cell in that phase, by status. Reads directly against the heatmap: the
    same 186 cells, aggregated instead of enumerated."""
    row_h, gap, label_w, pct_w = 30, 14, 190, 46
    bar_w = width - label_w - pct_w
    height = len(phase_distribution) * (row_h + gap) + gap

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        f'role="img" aria-label="Milestone status by phase, region-wide" preserveAspectRatio="xMinYMin meet">'
    ]
    y = gap
    for row in phase_distribution:
        total = row["total"] or 1
        completed = row["counts"]["C"]
        parts.append(
            f'<text x="0" y="{y + row_h/2 + 4:.1f}" font-size="12" font-weight="700" '
            f'font-family="Georgia,serif" fill="#14213D">{escape(row["short"])}</text>'
        )
        parts.append(
            f'<text x="26" y="{y + row_h/2 + 4:.1f}" font-size="10.5" '
            f'font-family="Calibri,Arial,sans-serif" fill="#5B6470">'
            f'{escape(row["phase"].split(" ", 1)[1] if " " in row["phase"] else "")}</text>'
        )
        x = label_w
        for status in ("C", "IP", "D", "NS", "NA"):
            n = row["counts"][status]
            if not n:
                continue
            seg_w = bar_w * n / total
            title = f'{STATUS_LABEL[status]}: {n} of {total}'
            parts.append(
                f'<g><title>{escape(title)}</title>'
                f'<rect x="{x:.1f}" y="{y}" width="{seg_w:.1f}" height="{row_h}" '
                f'fill="{STATUS_COLOR[status]}"/></g>'
            )
            x += seg_w
        parts.append(
            f'<text x="{label_w + bar_w + 10}" y="{y + row_h/2 + 4:.1f}" font-size="11" font-weight="700" '
            f'font-family="Calibri,Arial,sans-serif" fill="#14213D">{completed}/{total}</text>'
        )
        y += row_h + gap
    parts.append("</svg>")
    return "".join(parts)


def domain_overview_svg(domain_counts: list[tuple[str, int]], width: int = 720) -> str:
    """A horizontal bar per results domain, sized by how many indicators it
    holds — the map of section 4 before the reader scrolls through it."""
    row_h, gap, label_w = 26, 12, 170
    max_n = max((n for _, n in domain_counts), default=1)
    bar_w = width - label_w - 46
    height = len(domain_counts) * (row_h + gap) + gap

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        f'role="img" aria-label="Indicator count by domain" preserveAspectRatio="xMinYMin meet">'
    ]
    y = gap
    for domain, n in domain_counts:
        w = bar_w * n / max_n if max_n else 0
        parts.append(
            f'<text x="0" y="{y + row_h/2 + 4:.1f}" font-size="11.5" '
            f'font-family="Calibri,Arial,sans-serif" fill="#14213D">{escape(domain)}</text>'
        )
        parts.append(
            f'<rect x="{label_w}" y="{y}" width="{bar_w:.1f}" height="{row_h}" rx="4" fill="#EEEEE8"/>'
        )
        parts.append(
            f'<rect x="{label_w}" y="{y}" width="{w:.1f}" height="{row_h}" rx="4" fill="#0093D5"/>'
        )
        parts.append(
            f'<text x="{label_w + bar_w + 10}" y="{y + row_h/2 + 4:.1f}" font-size="11" font-weight="700" '
            f'font-family="Calibri,Arial,sans-serif" fill="#14213D">{n}</text>'
        )
        y += row_h + gap
    parts.append("</svg>")
    return "".join(parts)


def sparkbar_svg(pct: float, colour: str, width: int = 64, height: int = 8) -> str:
    pct = max(0.0, min(1.0, pct))
    return (
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" aria-hidden="true">'
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="4" fill="#EEEEE8"/>'
        f'<rect x="0" y="0" width="{width * pct:.1f}" height="{height}" rx="4" fill="{colour}"/>'
        f"</svg>"
    )
