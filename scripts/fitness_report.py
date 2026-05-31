"""
Fitness PDF report generator (planned vs. actual).

Charts: matplotlib (server-side PNGs, in-memory).
PDF:    ReportLab (no browser dependency).

Shows the PLANNED schedule the user set up — planned calorie intake per day and
planned workouts for the week — and overlays what was actually done. Days with no
logged data still appear, using the plan so the report can "show the future".

LANGUAGE REQUIREMENT
--------------------
All input data and all rendered text MUST be in English. The PDF uses the built-in
Helvetica font, which does not render Hebrew / Arabic / other non-Latin scripts
(they appear as blank boxes or mirrored). The bot must translate or romanize any
user-facing strings (workout type names, notes, plan name, etc.) to English BEFORE
passing them in.

Usage:
    generate_report(data, mode="daily",  out="report.pdf")
    generate_report(data, mode="weekly", out="report.pdf")

Install:
    pip install matplotlib reportlab
"""

import io
from datetime import date

import matplotlib
matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
)

# ---- theme ----------------------------------------------------------------
ACCENT     = colors.HexColor("#1f6feb")   # planned / primary
ACTUAL     = colors.HexColor("#22c55e")   # actual / done
MUTED      = colors.HexColor("#6b7280")
LIGHT      = colors.HexColor("#f3f4f6")
DARK       = colors.HexColor("#111827")
DONE_BG    = colors.HexColor("#dcfce7")   # green-tint row: completed
PENDING_BG = colors.HexColor("#fef9c3")   # yellow-tint row: planned / not yet done


# ---- chart helpers (return PNG bytes) -------------------------------------
def _fig_to_png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", transparent=True)
    plt.close(fig)
    buf.seek(0)
    return buf


def calories_planned_vs_actual(labels, planned, actual, target=None):
    """
    Grouped bars per day: planned intake vs actual intake.
    `actual` may contain None for days with no logged data — those days still
    show the planned bar (the "future"/prediction) and simply omit the actual bar.
    Optional `target` draws a dashed reference line.
    """
    n = len(labels)
    x = range(n)
    w = 0.4
    # Replace None in actual with 0 height but remember which were missing.
    actual_vals = [0 if v is None else v for v in actual]
    fig, ax = plt.subplots(figsize=(6.6, 2.9))
    ax.bar([i - w / 2 for i in x], planned, width=w,
           color="#1f6feb", label="Planned", alpha=0.55)
    # Only draw actual bars where data exists.
    ax_x = [i + w / 2 for i in x]
    ax.bar(ax_x, actual_vals, width=w, color="#22c55e", label="Actual")
    if target is not None:
        ax.axhline(target, color="#ef4444", ls="--", lw=1.2, label=f"Target {target}")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("kcal", fontsize=8)
    ax.legend(frameon=False, fontsize=8, loc="upper right", ncol=3)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=8)
    # Mark missing-actual days with a small "—" under the axis.
    for i, v in enumerate(actual):
        if v is None:
            ax.annotate("no data", (i + w / 2, 0), textcoords="offset points",
                        xytext=(0, 4), ha="center", fontsize=6, color="#9ca3af",
                        rotation=90)
    return _fig_to_png(fig)


def workout_type_bar(type_labels, planned_counts, done_counts):
    """Per workout-type: planned vs completed counts."""
    n = len(type_labels)
    x = range(n)
    w = 0.4
    fig, ax = plt.subplots(figsize=(6.6, 2.9))
    ax.bar([i - w / 2 for i in x], planned_counts, width=w, color="#1f6feb",
           alpha=0.55, label="Planned")
    ax.bar([i + w / 2 for i in x], done_counts, width=w, color="#22c55e",
           label="Done")
    ax.set_xticks(list(x))
    ax.set_xticklabels(type_labels, fontsize=8)
    ax.set_ylabel("workouts", fontsize=8)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=8)
    return _fig_to_png(fig)


# ---- layout helpers -------------------------------------------------------
def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("H", parent=ss["Title"], fontSize=20, textColor=DARK,
                          spaceAfter=2, alignment=0))
    ss.add(ParagraphStyle("Sub", fontSize=9.5, textColor=MUTED, spaceAfter=2))
    ss.add(ParagraphStyle("Sec", fontSize=13, textColor=ACCENT, spaceBefore=10,
                          spaceAfter=6, leading=16))
    ss.add(ParagraphStyle("TypeHdr", fontSize=10.5, textColor=DARK, spaceBefore=6,
                          spaceAfter=3, leading=13, fontName="Helvetica-Bold"))
    ss.add(ParagraphStyle("KpiV", fontSize=15, textColor=DARK, alignment=1,
                          leading=17, fontName="Helvetica-Bold"))
    ss.add(ParagraphStyle("KpiL", fontSize=7.5, textColor=MUTED, alignment=1))
    return ss


def kpi_row(items, S):
    cells = [[Paragraph(str(v), S["KpiV"]), Paragraph(str(l), S["KpiL"])] for l, v in items]
    inner = [Table([[c[0]], [c[1]]], style=TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ])) for c in cells]
    t = Table([inner], colWidths=[(170 * mm) / len(inner)] * len(inner))
    style = [
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.white),
        ("INNERGRID", (0, 0), (-1, -1), 3, colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    try:
        from reportlab import Version as _RLV
        if tuple(int(x) for x in _RLV.split(".")[:2]) >= (3, 6):
            style.append(("ROUNDEDCORNERS", [6, 6, 6, 6]))
    except Exception:
        pass
    t.setStyle(TableStyle(style))
    return t


def workout_table(rows, S):
    """
    rows: list of dicts: {"name", "detail", "done" (bool), "note"}
    Status-colored rows: green = done, yellow = planned/not done.
    """
    header = ["Workout", "Detail", "Status", "Note"]
    body = [header]
    status_rows = []
    for i, r in enumerate(rows, start=1):
        done = bool(r.get("done"))
        body.append([
            r.get("name", ""),
            r.get("detail", ""),
            "Done" if done else "Planned",
            r.get("note", ""),
        ])
        status_rows.append((i, done))
    t = Table(body, colWidths=[52 * mm, 46 * mm, 24 * mm, 48 * mm], repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("FONTNAME", (2, 1), (2, -1), "Helvetica-Bold"),
    ]
    for ridx, done in status_rows:
        style.append(("BACKGROUND", (0, ridx), (-1, ridx),
                      DONE_BG if done else PENDING_BG))
    t.setStyle(TableStyle(style))
    return t


def img(png, w_mm):
    im = Image(png)
    ratio = im.imageHeight / im.imageWidth
    im.drawWidth = w_mm * mm
    im.drawHeight = w_mm * mm * ratio
    return im


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(20 * mm, 12 * mm, f"Generated {date.today():%Y-%m-%d} - Fitness Bot")
    canvas.drawRightString(190 * mm, 12 * mm, f"Page {doc.page}")
    canvas.setStrokeColor(colors.HexColor("#e5e7eb"))
    canvas.line(20 * mm, 15 * mm, 190 * mm, 15 * mm)
    canvas.restoreState()


# ---- main -----------------------------------------------------------------
def generate_report(data, mode="weekly", out="report.pdf"):
    """
    Build a planned-vs-actual fitness PDF. See references/data_schema.md for the
    full input contract. All strings must be English (Helvetica can't render
    Hebrew/Arabic).

    Required keys (all modes):
        user, plan, range_label, summary_line
        kpis: [(label, value), ...]
        cal_labels:  [str, ...]            x-axis (days for weekly, meals/day for daily)
        cal_planned: [number, ...]         planned intake per label
        cal_actual:  [number|None, ...]    actual intake; None => no data (shows plan only)
        cal_target:  number | None         optional dashed reference line
        workouts_by_type: {
            "<Type name in English>": [
                {"name", "detail", "done": bool, "note"}, ...
            ], ...
        }
    Weekly also uses:
        type_summary: derived automatically from workouts_by_type if absent
    """
    S = _styles()
    doc = SimpleDocTemplate(out, pagesize=A4,
                            leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=18 * mm, bottomMargin=20 * mm)
    E = []

    # header
    E.append(Paragraph(f"{data['plan']} - {mode.title()} Report", S["H"]))
    E.append(Paragraph(f"{data['user']} - {data['range_label']}", S["Sub"]))
    E.append(Paragraph(data["summary_line"], S["Sub"]))
    E.append(Spacer(1, 4))
    E.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e5e7eb")))
    E.append(Spacer(1, 8))

    # KPI tiles
    E.append(kpi_row(data["kpis"], S))
    E.append(Spacer(1, 10))

    # calorie chart: planned vs actual
    E.append(Paragraph("Calorie Intake - Planned vs Actual", S["Sec"]))
    cals = img(calories_planned_vs_actual(
        data["cal_labels"], data["cal_planned"], data["cal_actual"],
        data.get("cal_target")), 168)
    E.append(cals)

    # workout-type summary chart (planned vs done counts)
    wbt = data.get("workouts_by_type", {})
    if wbt:
        type_labels = list(wbt.keys())
        planned_counts = [len(v) for v in wbt.values()]
        done_counts = [sum(1 for w in v if w.get("done")) for v in wbt.values()]
        E.append(Paragraph("Workouts by Type - Planned vs Done", S["Sec"]))
        E.append(img(workout_type_bar(type_labels, planned_counts, done_counts), 168))

    # workout detail, grouped by type
    if wbt:
        E.append(Paragraph("Workout Schedule", S["Sec"]))
        for tname, items in wbt.items():
            done_n = sum(1 for w in items if w.get("done"))
            E.append(Paragraph(f"{tname}  ({done_n}/{len(items)} done)", S["TypeHdr"]))
            if items:
                E.append(workout_table(items, S))
            else:
                E.append(Paragraph("No workouts planned.", S["Sub"]))
            E.append(Spacer(1, 4))

    doc.build(E, onFirstPage=_footer, onLaterPages=_footer)
    return out


# ---- demo data ------------------------------------------------------------
if __name__ == "__main__":
    weekly = {
        "user": "Alex R.",
        "plan": "Lean Cut",
        "range_label": "May 25 - May 31, 2026",
        "summary_line": "Goal: Cut - 1,800 kcal/day target - 4 workouts/week",
        "kpis": [
            ("Avg planned", "1,800"),
            ("Avg actual", "1,765"),
            ("Workouts done", "3/4"),
            ("Days logged", "4/7"),
        ],
        "cal_labels":  ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "cal_planned": [1800, 1800, 1800, 1800, 1800, 2000, 2000],
        "cal_actual":  [1720, 1850, 1690, 1810, None, None, None],  # Fri-Sun not logged yet
        "cal_target":  1800,
        "workouts_by_type": {
            "Strength": [
                {"name": "Lower Body A", "detail": "Squat, RDL, Lunge",
                 "done": True,  "note": "Felt strong"},
                {"name": "Upper Body A", "detail": "Bench, Row, Press",
                 "done": True,  "note": ""},
            ],
            "Core": [
                {"name": "Core Circuit", "detail": "Plank, Hollow, Leg raise",
                 "done": True,  "note": ""},
                {"name": "Core Circuit", "detail": "Plank, Hollow, Leg raise",
                 "done": False, "note": "Scheduled Sat"},
            ],
            "Cardio": [
                {"name": "Zone 2 Run", "detail": "40 min easy",
                 "done": False, "note": "Scheduled Sun"},
            ],
        },
    }
    generate_report(weekly, mode="weekly", out="/home/claude/weekly_demo.pdf")

    daily = {
        "user": "Alex R.",
        "plan": "Lean Cut",
        "range_label": "Saturday, May 31, 2026",
        "summary_line": "Goal: Cut - 1,800 kcal/day target",
        "kpis": [
            ("Planned", "1,800"),
            ("Actual", "1,210"),
            ("Remaining", "590"),
            ("Workout", "Planned"),
        ],
        "cal_labels":  ["Breakfast", "Lunch", "Snack", "Dinner"],
        "cal_planned": [420, 560, 210, 610],
        "cal_actual":  [420, 560, 230, None],   # dinner not logged yet
        "cal_target":  1800,
        "workouts_by_type": {
            "Strength": [
                {"name": "Lower Body B", "detail": "Deadlift, Split squat",
                 "done": False, "note": "Planned 6pm"},
            ],
        },
    }
    generate_report(daily, mode="daily", out="/home/claude/daily_demo.pdf")
    print("done")
