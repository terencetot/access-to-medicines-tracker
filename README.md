# Access to Medicines Tracking Platform (IGAP / Dementia)

WHO Regional Office for Africa · Disease Prevention and Control cluster · NCD and Mental Health team.

A static, self-contained HTML dashboard reporting on the Access to Medicines
initiative for neurological disorders and dementia across six countries:
Botswana, Cote d'Ivoire, Ethiopia, Gambia, Malawi and Zambia. Every figure on
screen is derived at build time from
`data/WHO_AFRO_Access_to_Medicines_Tracking_Matrix_v2.xlsx` — nothing is typed
by hand into the dashboard itself.

## Quick start

```bash
pip install -r requirements.txt
python main.py
```

This produces `output/AtM_AFRO_Dashboard.html` — a single file with no
external network calls (fonts, icons and every chart are inlined or hand-built
SVG), so it opens correctly from a USB stick with no internet connection.
Open it directly in a browser; there is no server to run.

## Pipeline

```
main.py
  1. src/extract.py          workbook -> output/data.json (normalised, verbatim)
  2. scripts/validate_data.py  data contract checks against data.json
  3. src/test_compute.py     unit tests for every derived measure
  4. src/render.py           data.json + templates -> output/AtM_AFRO_Dashboard.html
```

Each step can also be run on its own from its own directory (`src/` or
`scripts/`), which is useful when iterating on one stage without rebuilding
the rest.

### Why the build does not stop on the current validation failures

`scripts/validate_data.py` is a strict, standalone data-contract gate. Run
today, it reports ~36 violations, every one of them a milestone coded `C`
(completed) with no actual date on file. This is not a bug in the workbook or
the script: it is the "v1 carry-over, unverified" data explicitly flagged in
the workbook's own `00_README` sheet and `10_Data_Quality_Log` (issue DQ-07).
`main.py` prints the report in full, recognises that every failure is of this
one known and expected shape, and continues the build — because the entire
point of the dashboard's provisional-data chip and per-country evidence
coverage figure is to surface exactly this condition prominently, not hide it
behind a failed build. Any violation of a *different* shape (a duplicate
`ISO3|MilestoneID` key, an unknown status code, an ISO3 missing from the
country register, a results value with no data source) still aborts the
build — see `main.py`'s `KNOWN_FAILURE_MARKERS`.

## Data contract

Source workbook sheets (see `00_README` inside the workbook for the full
narrative):

| Sheet | Content | Notes |
|---|---|---|
| `01_Country_Register` | one row per country | ISO3 is the join key everywhere |
| `02_Milestone_Catalogue` | 31 milestones, phases P1-P5 | weight, means of verification |
| `03_Progress_Tracker` | 186 rows (6 countries x 31 milestones) | the single source of truth for implementation status |
| `04_Matrix_View` | formula view of sheet 03 | **never read** — rebuilt live by the dashboard instead |
| `05_Results_Framework` | 204 rows (34 indicators x 6 countries) | row 6 is a worked example and is skipped |
| `06_Indicator_Metadata` | 34 indicator definitions | rendered verbatim in the methods annex |
| `07_Tracer_Basket` | 23 medicines and care products | plus 5 standing notes carried in the same column |
| `08_Regional_Dashboard` | formula roll-up of sheet 03 | **never read** — recomputed from sheet 03 instead |
| `09_Risk_Register` | 8 risks | plus 1 scoring-convention note carried in the same column |
| `10_Data_Quality_Log` | 10 logged issues | rendered verbatim in the methods annex |
| `11_Reference_Lists` | controlled vocabularies | status codes etc. |

Status vocabulary: `NS` not started, `IP` in progress, `C` completed, `D`
delayed, `NA` not applicable.

Derived measures (`src/compute.py`, one function per measure, unit tested in
`src/test_compute.py`):

- `milestone_completion_rate(iso)` = count(status == C) / count(status != NA)
- `weighted_progress_index(iso)` = sum(weight x score) / sum(weight where
  status != NA), score C=1.00, IP=0.50, D=0.25, NS=0.00
- `evidence_coverage(iso)` = count(status == C and verified == Yes) /
  count(status == C)
- `phase_position(iso)` = the highest phase with at least one milestone C or IP
- `regional_rollup(milestone_id)` = countries with that milestone at C, over
  countries where it is applicable
- `indicator_gap(code, iso)` = target minus latest value, signed by the
  indicator's direction so a positive gap always means distance still to travel

Hand-checked case: Ethiopia comes out at 12 completed of 31 applicable
milestones, completion rate 38.7%, weighted index 40.3% — verified in
`test_compute.py::test_ethiopia_hand_checked_case` against the real workbook.

## Design

- Palette: WHO navy `#00205B`, WHO light blue `#0093D5` accent, warm neutral
  background `#FAFAF8`. Status colour is never the only signal — every status
  is also a letter (`C`/`IP`/`D`/`NS`/`NA`).
- Type: Georgia (serif, headings and big numbers) and Calibri (sans, interface
  and data), both system fonts — no web font is loaded, which keeps the build
  fully offline.
- Charts are hand-built inline SVG generated in `src/charts.py` at build time
  (phase pipeline, dual progress bars, risk matrix) — no charting library, so
  a screenshot of a chart and a reading of its table can never disagree.
- Layout is a fixed left-hand navigation with the eight report sections
  anchored on one continuous, printable page, rather than a tabbed interface.
- Accessible: 4.5:1 contrast targets, full keyboard navigation (heatmap cells
  and risk points are focusable and carry the same detail as on hover),
  `prefers-reduced-motion` respected, semantic heading order.
- Print: an A4 landscape stylesheet; the regional summary and the heatmap
  each print on their own page.

## About the logos

The badge in the left navigation is a plain custom mark, not the official WHO
emblem. The WHO emblem is a protected mark (Paris Convention, Article 6ter)
and reproducing it accurately requires the organisation's own authorised
artwork, which was not supplied with this project. If you have that artwork
and the authority to use it, replace `.brand-mark` in
`assets/tokens.css` / `templates/partials/side_nav.html.j2` with the real logo.

## Quarterly update procedure

1. Replace `data/WHO_AFRO_Access_to_Medicines_Tracking_Matrix_v2.xlsx` with
   the refreshed workbook (same sheet structure and header rows).
2. Run `python main.py` from the project root.
3. Read the validation report in full. If any violation is *not* one already
   described above, fix the workbook before re-running — do not edit
   `output/data.json` by hand.
4. Check the unit test output, in particular that the hand-checked case still
   passes (or update it, with sign-off, if the workbook's own reference case
   has genuinely changed).
5. Open `output/AtM_AFRO_Dashboard.html` and check the header status chip and
   footer record counts against what you expect for the new reporting period.

## Repository layout

```
access-to-medicines-tracker/
  data/           WHO_AFRO_Access_to_Medicines_Tracking_Matrix_v2.xlsx (input, read only)
  src/
    extract.py        workbook -> data.json
    compute.py         derived measures
    charts.py          hand-built inline SVG chart generation
    render.py          Jinja2 render to the single output HTML
    test_compute.py    unit tests, incl. the Ethiopia hand-checked case
    templates/
      dashboard.html.j2
      partials/*.j2
  assets/
    tokens.css      design tokens, inlined at build time
    icons.svg        hand-built icon sprite, inlined at build time
  scripts/
    validate_data.py  data contract checks, run before every build
  output/
    AtM_AFRO_Dashboard.html   the single self-contained artefact
    data.json                  the extracted dataset, for inspection
  main.py           orchestrates extract, validate, test, render
  requirements.txt
```
