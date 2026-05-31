---
name: fitness-report-pdf
description: Generate polished PDF reports for a fitness bot covering food (nutrition/macros/calories) and workouts (exercises/sets/training volume), with embedded charts. Use this skill whenever the user wants to produce a fitness, nutrition, diet, meal, or workout report/summary as a PDF — including daily or weekly summaries, progress reports, or any request to "export", "generate a PDF", or "send a report" of logged food and training data. Trigger even if the user doesn't say the word "PDF" explicitly, as long as they want a shareable document of fitness/nutrition/workout data. Charts are rendered server-side with matplotlib (no browser dependency), and the PDF is built with ReportLab, so this runs cleanly inside a bot process.
---

# Fitness Report PDF

Generates a clean, branded PDF report for a fitness bot. Two layouts share one entry point:

- **daily** — header + KPI tiles, macro donut + per-meal calories bar, nutrition table (with totals), workout table.
- **weekly** — everything in daily, plus a second chart row: bodyweight trend line + training-volume bar.

Charts are matplotlib PNGs rendered in-memory (headless `Agg` backend), embedded into a ReportLab document. No Chromium / wkhtmltopdf dependency, so it drops straight into a server or bot worker.

## Dependencies

Pinned in `requirements.txt` at the repo root:

```
pip install -r requirements.txt
```

(That installs `matplotlib` and `reportlab`.)

## How to use it

The generator lives in `scripts/fitness_report.py`. The single entry point is:

```python
from fitness_report import generate_report

generate_report(data, mode="weekly", out="report.pdf")   # write to disk
```

To return bytes instead of writing a file (e.g. to attach to a bot message), pass a buffer — `SimpleDocTemplate` accepts any file-like object:

```python
import io
buf = io.BytesIO()
generate_report(data, mode="daily", out=buf)
buf.seek(0)
pdf_bytes = buf.read()
```

`mode` is `"daily"` or `"weekly"`. The only difference in required `data` is that weekly also needs `weight_labels`, `weights`, `vol_labels`, and `vol_values` for the second chart row.

## Building the `data` dict

The caller (the bot) is responsible for assembling logged food and workouts into the `data` dict, then calling `generate_report`. The full field-by-field schema, with both a daily and a weekly example, is in `references/data_schema.md` — read it before constructing `data` so every required key is present and shaped correctly. A missing key will raise a `KeyError` at build time.

Quick shape reference (see the reference file for details):

```python
data = {
    "user": str, "plan": str, "range_label": str, "summary_line": str,
    "kpis": [(label, value), ...],            # 3-4 tiles recommended
    "macros": {"protein": g, "carbs": g, "fat": g},
    "cal_labels": [...], "cal_intake": [...], "cal_target": int,
    # weekly only:
    "weight_labels": [...], "weights": [...],
    "vol_labels": [...], "vol_values": [...],
    "nutrition": {"header": [...], "rows": [[...], ...], "totals": [...]},
    "workout":   {"header": [...], "rows": [[...], ...]},
}
```

## Customization

These are intentional, low-risk edits — make them when the user asks:

- **Brand colors**: constants at the top of `fitness_report.py` (`ACCENT`, `ACCENT_2`, `MACRO_COLORS`, etc.).
- **Footer text**: the `_footer()` function (currently "OpenClaw Fitness Bot"). Update for the bot's name.
- **Logo**: add a ReportLab `Image` flowable in the header section of `generate_report`.
- **Extra charts**: follow the existing chart-helper pattern — a function that builds a matplotlib figure and returns `_fig_to_png(fig)`, then embed via `img(png_bytes, width_mm)`.

## Notes / gotchas

- The script forces the matplotlib `Agg` backend at import time, which is what allows it to run in a headless bot process. Don't remove that line.
- `ROUNDEDCORNERS` is guarded for ReportLab < 3.6, so it degrades gracefully to square tiles on older versions rather than crashing.
- Each chart is closed (`plt.close`) after rendering to avoid leaking figures in a long-running process.
- To sanity-check the layout, run `python scripts/fitness_report.py` — it writes `weekly_demo.pdf` and `daily_demo.pdf` using built-in sample data.
