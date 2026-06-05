---
name: fitness-report-pdf
description: Generate polished PDF reports for a fitness bot covering planned vs. actual calorie intake and planned vs. completed workouts (grouped by client-defined types like Strength, Core, Cardio), with embedded charts. Use this skill whenever the user wants to produce a fitness, nutrition, diet, calorie, or workout report/summary as a PDF — including daily or weekly summaries, progress or schedule reports, or any request to "export", "generate a PDF", or "send a report" of planned and logged training/calorie data. The report shows the plan ("the future") even when actual data is missing for some days. Trigger even if the user doesn't say the word "PDF" explicitly, as long as they want a shareable document of fitness/calorie/workout data. All input and output text must be English. Charts are rendered server-side with matplotlib (no browser dependency) and the PDF is built with ReportLab, so this runs cleanly inside a bot process.
---

# Fitness Report PDF (planned vs. actual)

Generates a clean, branded PDF for a fitness bot. The report is built around the
user's **plan**, so it shows upcoming days and scheduled workouts even when no
actual data has been logged yet ("show the future"). One entry point, two framings:

- **daily** — KPI tiles, planned-vs-actual calorie chart (per meal), workouts-by-type chart + schedule.
- **weekly** — same, with the calorie chart spanning the week's days.

What it shows:
- **Calories** — planned intake per day/meal as bars, with actual logged intake
  overlaid. In weekly mode the week is always rendered Sunday→Saturday (from dated
  entries, any order, missing days filled). Days with no logged data still show the
  plan and are marked "no data". An optional dashed target line.
- **Overall progress** — two semicircular gauges: workouts completed (done vs
  planned) and calorie adherence (actual vs planned %, colored by how close).
- **Workouts** — grouped by **client-defined type** (e.g. Strength, Core, Cardio),
  with a status-colored table listing each workout as Done (green) or Planned (yellow).
- **Day-by-day detail** (optional) — a per-day page showing each day's workouts and
  the food eaten that day (name + calories + protein/carbs/fat, with totals).

Charts are matplotlib PNGs rendered in-memory (headless `Agg` backend), embedded
into a ReportLab document. No Chromium / wkhtmltopdf dependency.

## LANGUAGE: English only (hard requirement)

All strings passed in `data` — and therefore all text in the PDF — MUST be English.
The PDF uses ReportLab's built-in Helvetica, which cannot render Hebrew, Arabic, or
other non-Latin scripts (they appear blank or mirrored). The bot must translate or
romanize every user-facing string (plan name, workout type names, workout names,
details, notes, KPI labels) to English BEFORE building the dict. The client-chosen
workout *type* names are free text but must be supplied in English.

## Dependencies

Pinned in `requirements.txt` at the repo root:

```
pip install -r requirements.txt
```

(That installs `matplotlib` and `reportlab`.)

## How to use it

The generator lives in `scripts/fitness_report.py`. Single entry point:

```python
from fitness_report import generate_report

generate_report(data, mode="weekly", out="report.pdf")   # write to disk
```

To return bytes instead of writing a file (e.g. to attach to a bot message), pass a
buffer — `SimpleDocTemplate` accepts any file-like object:

```python
import io
buf = io.BytesIO()
generate_report(data, mode="daily", out=buf)
pdf_bytes = buf.getvalue()
```

`mode` is `"daily"` or `"weekly"`; it only affects framing/labels you supply (there
are no mode-specific required keys).

## Building the `data` dict

The bot assembles the plan + logged data into the `data` dict, then calls
`generate_report`. Read `references/data_schema.md` for the full field-by-field
contract with daily and weekly examples before constructing `data`; a missing
required key raises `KeyError` at build time.

Quick shape (see the reference for details):

```python
data = {
    "user": str, "plan": str, "range_label": str, "summary_line": str,
    "kpis": [(label, value), ...],          # 3-4 tiles
    "cal_target":  number | None,           # optional dashed line

    # WEEKLY calories: dated entries, any order, gaps OK.
    # Always rendered Sunday -> Saturday; missing days auto-filled.
    "cal_days": [
        {"date": "YYYY-MM-DD", "planned": number, "actual": number | None},
        ...
    ],
    "week_of": "YYYY-MM-DD",                 # optional; defaults to week of earliest date

    # DAILY calories instead use per-meal parallel lists:
    # "cal_labels": [str, ...], "cal_planned": [number, ...], "cal_actual": [number|None, ...]

    "workouts_by_type": {                   # client-defined English type names
        "Strength": [
            {"name": str, "detail": str, "done": bool, "note": str},
            ...
        ],
        "Core": [ ... ],
    },

    # OPTIONAL day-by-day detail page: each day's workouts + food eaten.
    "days": [
        {
            "label": str,                   # day heading, English
            "workouts": [ {"name", "detail", "done", "note"}, ... ],
            "foods": [ {"name", "kcal", "protein", "carbs", "fat"}, ... ],
        },
        ...
    ],
}
```

Weekly calorie days are always ordered **Sunday → Saturday** by the skill, no matter
what order `cal_days` is sent in, and any missing weekday is filled so all seven
columns always show. Use `None` (not `0`) for a day's `actual` when it isn't logged
yet, so the chart shows the plan and a "no data" marker instead of a logged zero.

## Customization

- **Brand / status colors**: constants at the top of `fitness_report.py` — `ACCENT`
  (planned), `ACTUAL` (done/green), `DONE_BG`, `PENDING_BG` (table row tints).
- **Footer text**: the `_footer()` function (currently "Fitness Bot").
- **Logo**: add a ReportLab `Image` flowable in the header section of `generate_report`.
- **Extra charts**: follow the existing pattern — a function that builds a matplotlib
  figure and returns `_fig_to_png(fig)`, then embed via `img(png_bytes, width_mm)`.

## Notes / gotchas

- All text must be English (see the language section) — this is the most common
  source of broken-looking PDFs.
- The script forces the matplotlib `Agg` backend at import; needed for headless bot
  processes. Don't remove it.
- `ROUNDEDCORNERS` is guarded for ReportLab < 3.6 (degrades to square tiles).
- Each chart is closed (`plt.close`) after rendering to avoid leaking figures.
- Keep `cal_planned` and `cal_actual` the same length as `cal_labels`.
- To sanity-check layout, run `python scripts/fitness_report.py` — it writes
  `weekly_demo.pdf` and `daily_demo.pdf` from built-in sample data.
