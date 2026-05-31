# fitness-report-pdf

A skill that generates polished PDF reports for a fitness bot — covering **planned
vs. actual calorie intake** and **planned vs. completed workouts** (grouped by
client-defined types like Strength / Core / Cardio), with embedded charts. The
report is built around the user's plan, so it shows the schedule ("the future")
even when actual data is missing for some days.

- Charts: matplotlib, rendered server-side as in-memory PNGs (headless `Agg` backend — no browser).
- PDF: ReportLab (no Chromium / wkhtmltopdf dependency).
- Two framings from one entry point: **daily** and **weekly**.
- **All input and output text must be English** (the built-in PDF font can't render Hebrew/Arabic).

## Repo layout

```
fitness-report-pdf/
├── SKILL.md                     # skill instructions + triggering description
├── requirements.txt             # matplotlib, reportlab
├── scripts/
│   └── fitness_report.py        # the generator (entry point: generate_report)
└── references/
    └── data_schema.md           # full input-dict contract + examples
```

## Use as a skill

Point your skill system (e.g. OpenClaw) at this folder. It reads `SKILL.md` (kept at the
repo root) to learn when to trigger and how to call the generator. The runtime must have the
dependencies installed:

```
pip install -r requirements.txt
```

## Use the generator directly

```python
from scripts.fitness_report import generate_report

generate_report(data, mode="weekly", out="report.pdf")   # write to disk

import io                                                  # or return bytes
buf = io.BytesIO()
generate_report(data, mode="daily", out=buf)
pdf_bytes = buf.getvalue()
```

See `references/data_schema.md` for the shape of `data`, with daily and weekly examples.

## Smoke test

```
python scripts/fitness_report.py   # writes weekly_demo.pdf + daily_demo.pdf
```
