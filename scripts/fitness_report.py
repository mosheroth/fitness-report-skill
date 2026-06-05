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
from datetime import date, datetime, timedelta

import matplotlib
matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable,
    PageBreak
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


def _parse_date(d):
    """Accept a date/datetime or an ISO 'YYYY-MM-DD' string; return a date."""
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    return datetime.strptime(str(d)[:10], "%Y-%m-%d").date()


def _week_sunday(anchor):
    """Return the Sunday on or before `anchor` (Python weekday: Mon=0..Sun=6)."""
    return anchor - timedelta(days=(anchor.weekday() + 1) % 7)


def build_sun_to_sat(cal_days, week_of=None):
    """
    Normalize dated calorie entries into a fixed Sunday->Saturday week.

    cal_days: list of dicts, each {"date": <date|'YYYY-MM-DD'>, "planned": number,
              "actual": number|None}. Order does not matter; gaps are allowed.
    week_of:  optional date/str anchoring the week. If None, the week containing
              the earliest entry is used.

    Returns (labels, planned, actual) as 7-element lists, Sunday first.
    Missing days get planned=0 and actual=None so the chart still shows all 7 days.
    """
    parsed = []
    for r in cal_days:
        parsed.append((_parse_date(r["date"]), r.get("planned", 0), r.get("actual")))
    if not parsed and week_of is None:
        raise ValueError("build_sun_to_sat needs either cal_days or week_of")

    anchor = _parse_date(week_of) if week_of is not None else min(p[0] for p in parsed)
    sunday = _week_sunday(anchor)
    week = [sunday + timedelta(days=i) for i in range(7)]
    by_date = {d: (pl, ac) for d, pl, ac in parsed}

    labels, planned, actual = [], [], []
    for d in week:
        pl, ac = by_date.get(d, (0, None))
        labels.append(d.strftime("%a"))   # Sun, Mon, ... Sat (English)
        planned.append(pl)
        actual.append(ac)
    return labels, planned, actual


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




def _draw_gauge(ax, pct, title, center_label):
    """Draw a single semicircular gauge on the given axes. pct in 0..100+."""
    import numpy as np
    pct_clamped = max(0.0, min(pct, 100.0))
    # color by completion
    if pct_clamped >= 90:
        fill = "#22c55e"
    elif pct_clamped >= 60:
        fill = "#f59e0b"
    else:
        fill = "#ef4444"

    # background arc (180deg -> 0deg, i.e. left to right over the top)
    theta = np.linspace(np.pi, 0, 200)
    ax.plot(np.cos(theta), np.sin(theta), lw=14, color="#e5e7eb",
            solid_capstyle="round")
    # filled portion
    frac = pct_clamped / 100.0
    theta_f = np.linspace(np.pi, np.pi - np.pi * frac, max(2, int(200 * frac)))
    ax.plot(np.cos(theta_f), np.sin(theta_f), lw=14, color=fill,
            solid_capstyle="round")
    # center text
    ax.text(0, 0.18, center_label, ha="center", va="center",
            fontsize=20, fontweight="bold", color="#111827")
    ax.text(0, -0.12, title, ha="center", va="center",
            fontsize=10, color="#6b7280")
    ax.set_xlim(-1.25, 1.25)
    ax.set_ylim(-0.3, 1.25)
    ax.set_aspect("equal")
    ax.axis("off")


def gauges_pair(workout_pct, workout_label, nutrition_pct, nutrition_label):
    """Two semicircular gauges side by side: workouts and nutrition."""
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.4))
    _draw_gauge(axes[0], workout_pct, "Workouts completed", workout_label)
    _draw_gauge(axes[1], nutrition_pct, "Calorie adherence", nutrition_label)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02, wspace=0.1)
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
    # Cell paragraph styles so long text wraps within the column width
    # instead of overflowing into adjacent cells.
    cell = ParagraphStyle("wo_cell", fontName="Helvetica", fontSize=8.5,
                          leading=10.5, textColor=DARK)
    cell_b = ParagraphStyle("wo_cell_b", parent=cell, fontName="Helvetica-Bold")
    hdr = ParagraphStyle("wo_hdr", fontName="Helvetica-Bold", fontSize=8.5,
                         leading=10.5, textColor=colors.white)

    def esc(s):
        # Paragraph parses minimal XML; escape so &, <, > in user text are literal.
        return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

    header = [Paragraph(h, hdr) for h in ("Workout", "Detail", "Status", "Note")]
    body = [header]
    status_rows = []
    for i, r in enumerate(rows, start=1):
        done = bool(r.get("done"))
        body.append([
            Paragraph(esc(r.get("name", "")), cell_b),
            Paragraph(esc(r.get("detail", "")), cell),
            Paragraph("Done" if done else "Planned", cell_b),
            Paragraph(esc(r.get("note", "")), cell),
        ])
        status_rows.append((i, done))
    t = Table(body, colWidths=[52 * mm, 46 * mm, 24 * mm, 48 * mm], repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    for ridx, done in status_rows:
        style.append(("BACKGROUND", (0, ridx), (-1, ridx),
                      DONE_BG if done else PENDING_BG))
    t.setStyle(TableStyle(style))
    return t


def food_table(items, S):
    """
    items: list of dicts {"name", "kcal", "protein", "carbs", "fat"}.
    Renders a compact meal table with a totals row. Numbers may be int/float/str.
    """
    cell = ParagraphStyle("food_cell", fontName="Helvetica", fontSize=8,
                          leading=10, textColor=DARK)
    cell_r = ParagraphStyle("food_cell_r", parent=cell, alignment=2)  # right
    hdr = ParagraphStyle("food_hdr", fontName="Helvetica-Bold", fontSize=8,
                         leading=10, textColor=colors.white)
    hdr_r = ParagraphStyle("food_hdr_r", parent=hdr, alignment=2)

    def esc(s):
        return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

    def num(v):
        if v is None or v == "":
            return "-"
        if isinstance(v, float) and v.is_integer():
            v = int(v)
        return str(v)

    header = [Paragraph("Food", hdr),
              Paragraph("kcal", hdr_r), Paragraph("P", hdr_r),
              Paragraph("C", hdr_r), Paragraph("F", hdr_r)]
    body = [header]
    tot = {"kcal": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
    have = {"kcal": False, "protein": False, "carbs": False, "fat": False}
    for it in items:
        for k in tot:
            v = it.get(k)
            if isinstance(v, (int, float)):
                tot[k] += v
                have[k] = True
        body.append([
            Paragraph(esc(it.get("name", "")), cell),
            Paragraph(num(it.get("kcal")), cell_r),
            Paragraph(num(it.get("protein")), cell_r),
            Paragraph(num(it.get("carbs")), cell_r),
            Paragraph(num(it.get("fat")), cell_r),
        ])
    # totals row (only sums columns that had at least one numeric value)
    tcell = ParagraphStyle("food_tot", parent=cell, fontName="Helvetica-Bold")
    tcell_r = ParagraphStyle("food_tot_r", parent=tcell, alignment=2)
    body.append([
        Paragraph("Total", tcell),
        Paragraph(num(round(tot["kcal"])) if have["kcal"] else "-", tcell_r),
        Paragraph(num(round(tot["protein"])) if have["protein"] else "-", tcell_r),
        Paragraph(num(round(tot["carbs"])) if have["carbs"] else "-", tcell_r),
        Paragraph(num(round(tot["fat"])) if have["fat"] else "-", tcell_r),
    ])
    t = Table(body, colWidths=[78 * mm, 24 * mm, 22 * mm, 22 * mm, 24 * mm],
              repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACTUAL),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e0ecff")),
    ]))
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
        cal_target:  number | None         optional dashed reference line
        workouts_by_type: {
            "<Type name in English>": [
                {"name", "detail", "done": bool, "note"}, ...
            ], ...
        }

    Calorie input depends on mode:
      WEEKLY: provide `cal_days`, a list of dated entries (any order, gaps OK):
          cal_days: [{"date": "YYYY-MM-DD", "planned": num, "actual": num|None}, ...]
        The week is ALWAYS rendered Sunday -> Saturday. Missing days are filled
        (planned=0, actual=None) so all 7 weekday columns always appear. Optionally
        pass `week_of` ("YYYY-MM-DD") to pick the week explicitly; otherwise the week
        containing the earliest entry is used.
      DAILY: provide the per-meal lists directly (dates don't apply to meals):
          cal_labels: [str, ...]; cal_planned: [num, ...]; cal_actual: [num|None, ...]
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
    # Weekly is always normalized to a fixed Sunday->Saturday week from dated
    # entries; daily uses the per-meal lists as given.
    if mode == "weekly":
        cal_labels, cal_planned, cal_actual = build_sun_to_sat(
            data["cal_days"], week_of=data.get("week_of"))
    else:
        cal_labels = data["cal_labels"]
        cal_planned = data["cal_planned"]
        cal_actual = data["cal_actual"]

    E.append(Paragraph("Calorie Intake - Planned vs Actual", S["Sec"]))
    cals = img(calories_planned_vs_actual(
        cal_labels, cal_planned, cal_actual, data.get("cal_target")), 168)
    E.append(cals)

    # Two overall gauges: workout completion and calorie adherence.
    wbt = data.get("workouts_by_type", {})
    all_workouts = [w for items in wbt.values() for w in items]
    total_planned_workouts = len(all_workouts)
    total_done_workouts = sum(1 for w in all_workouts if w.get("done"))
    workout_pct = (100.0 * total_done_workouts / total_planned_workouts
                   if total_planned_workouts else 0.0)
    workout_label = f"{total_done_workouts}/{total_planned_workouts}"

    # Calorie adherence: how close actual total is to planned total.
    # Only days with logged actual count toward both sides (fair comparison).
    planned_sum = 0.0
    actual_sum = 0.0
    for pl, ac in zip(cal_planned, cal_actual):
        if ac is not None:
            planned_sum += (pl or 0)
            actual_sum += ac
    if planned_sum > 0:
        nutrition_pct = 100.0 * actual_sum / planned_sum
        nutrition_label = f"{round(nutrition_pct)}%"
    else:
        nutrition_pct = 0.0
        nutrition_label = "no data"

    E.append(Paragraph("Overall Progress", S["Sec"]))
    E.append(img(gauges_pair(workout_pct, workout_label,
                             nutrition_pct, nutrition_label), 150))

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

    # day-by-day detail: per day, workouts done + food eaten that day
    days = data.get("days")
    if days:
        E.append(PageBreak())
        E.append(Paragraph("Day-by-Day Detail", S["Sec"]))
        for d in days:
            E.append(Paragraph(d.get("label", ""), S["TypeHdr"]))
            wos = d.get("workouts", [])
            if wos:
                E.append(workout_table(wos, S))
                E.append(Spacer(1, 3))
            else:
                E.append(Paragraph("No workouts.", S["Sub"]))
            foods = d.get("foods", [])
            if foods:
                E.append(food_table(foods, S))
            else:
                E.append(Paragraph("No food logged.", S["Sub"]))
            E.append(Spacer(1, 8))

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
        # Dated entries in deliberately shuffled order with a couple of days
        # missing — the report still renders a full Sunday..Saturday week.
        # (Week of May 24 2026 is Sun May 24 .. Sat May 30.)
        "cal_days": [
            {"date": "2026-05-27", "planned": 1800, "actual": 1690},  # Wed
            {"date": "2026-05-24", "planned": 1800, "actual": 1720},  # Sun
            {"date": "2026-05-26", "planned": 1800, "actual": 1850},  # Tue
            {"date": "2026-05-25", "planned": 1800, "actual": 1810},  # Mon
            {"date": "2026-05-28", "planned": 1800, "actual": None},  # Thu (not logged)
            # Fri May 29 and Sat May 30 omitted entirely -> auto-filled
        ],
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
        # Day-by-day detail: each day's workouts + food eaten that day.
        "days": [
            {
                "label": "Sunday, May 24",
                "workouts": [
                    {"name": "Lower Body A", "detail": "Squat, RDL, Lunge",
                     "done": True, "note": "Felt strong"},
                ],
                "foods": [
                    {"name": "Oats with berries", "kcal": 420, "protein": 18, "carbs": 62, "fat": 10},
                    {"name": "Chicken rice bowl", "kcal": 560, "protein": 45, "carbs": 55, "fat": 16},
                    {"name": "Greek yogurt", "kcal": 180, "protein": 18, "carbs": 12, "fat": 6},
                    {"name": "Salmon & veg", "kcal": 560, "protein": 42, "carbs": 30, "fat": 26},
                ],
            },
            {
                "label": "Monday, May 25",
                "workouts": [
                    {"name": "Upper Body A", "detail": "Bench, Row, Press",
                     "done": True, "note": ""},
                ],
                "foods": [
                    {"name": "Eggs & toast", "kcal": 400, "protein": 26, "carbs": 30, "fat": 18},
                    {"name": "Turkey wrap", "kcal": 520, "protein": 40, "carbs": 48, "fat": 18},
                    {"name": "Protein shake", "kcal": 230, "protein": 30, "carbs": 12, "fat": 5},
                    {"name": "Beef stir-fry", "kcal": 660, "protein": 46, "carbs": 52, "fat": 28},
                ],
            },
            {
                "label": "Tuesday, May 26",
                "workouts": [
                    {"name": "Core Circuit", "detail": "Plank, Hollow, Leg raise",
                     "done": True, "note": ""},
                ],
                "foods": [
                    {"name": "Smoothie bowl", "kcal": 380, "protein": 20, "carbs": 58, "fat": 9},
                    {"name": "Tuna salad", "kcal": 480, "protein": 42, "carbs": 22, "fat": 24},
                    {"name": "Apple & PB", "kcal": 220, "protein": 6, "carbs": 28, "fat": 11},
                    {"name": "Pasta bolognese", "kcal": 770, "protein": 38, "carbs": 88, "fat": 26},
                ],
            },
        ],
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
