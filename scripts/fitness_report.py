"""
Fitness PDF report generator.
Charts: matplotlib (server-side PNGs, in-memory).
PDF: ReportLab (no browser dependency).

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
ACCENT   = colors.HexColor("#1f6feb")
ACCENT_2 = colors.HexColor("#22c55e")
MUTED    = colors.HexColor("#6b7280")
LIGHT    = colors.HexColor("#f3f4f6")
DARK     = colors.HexColor("#111827")
MACRO_COLORS = ["#1f6feb", "#22c55e", "#f59e0b"]  # P / C / F


# ---- chart helpers (return PNG bytes) -------------------------------------
def _fig_to_png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", transparent=True)
    plt.close(fig)
    buf.seek(0)
    return buf


def macro_donut(protein_g, carbs_g, fat_g):
    total = max(protein_g + carbs_g + fat_g, 1)
    fig, ax = plt.subplots(figsize=(3.2, 3.2))
    vals = [protein_g, carbs_g, fat_g]
    ax.pie(vals, colors=MACRO_COLORS, startangle=90,
           wedgeprops=dict(width=0.42, edgecolor="white"),
           autopct=lambda p: f"{p:.0f}%", pctdistance=0.78,
           textprops=dict(color="white", fontsize=9, weight="bold"))
    ax.text(0, 0, f"{int(total)}g", ha="center", va="center",
            fontsize=13, weight="bold", color="#111827")
    ax.legend(["Protein", "Carbs", "Fat"], loc="lower center",
              bbox_to_anchor=(0.5, -0.12), ncol=3, frameon=False, fontsize=8)
    return _fig_to_png(fig)


def calories_bar(labels, intake, target):
    fig, ax = plt.subplots(figsize=(6.4, 2.6))
    x = range(len(labels))
    ax.bar(x, intake, color="#1f6feb", width=0.6, label="Intake")
    ax.axhline(target, color="#ef4444", ls="--", lw=1.3, label=f"Target {target}")
    ax.set_xticks(list(x)); ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("kcal", fontsize=8)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=8)
    return _fig_to_png(fig)


def weight_line(labels, weights):
    fig, ax = plt.subplots(figsize=(6.4, 2.6))
    ax.plot(labels, weights, color="#22c55e", marker="o", lw=2, ms=5)
    ax.fill_between(range(len(weights)), weights, min(weights) - 0.5,
                    color="#22c55e", alpha=0.08)
    ax.set_ylabel("kg", fontsize=8)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=8)
    return _fig_to_png(fig)


def volume_bar(labels, volumes):
    fig, ax = plt.subplots(figsize=(6.4, 2.6))
    ax.bar(labels, volumes, color="#8b5cf6", width=0.6)
    ax.set_ylabel("sets", fontsize=8)
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
    ss.add(ParagraphStyle("KpiV", fontSize=15, textColor=DARK, alignment=1,
                          leading=17, fontName="Helvetica-Bold"))
    ss.add(ParagraphStyle("KpiL", fontSize=7.5, textColor=MUTED, alignment=1))
    return ss


def kpi_row(items, S):
    """items = [(label, value), ...]"""
    cells = [[Paragraph(v, S["KpiV"]), Paragraph(l, S["KpiL"])] for l, v in items]
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
    # ROUNDEDCORNERS needs ReportLab >= 3.6; guard so older versions don't throw.
    try:
        from reportlab import Version as _RLV
        if tuple(int(x) for x in _RLV.split(".")[:2]) >= (3, 6):
            style.append(("ROUNDEDCORNERS", [6, 6, 6, 6]))
    except Exception:
        pass
    t.setStyle(TableStyle(style))
    return t


def data_table(header, rows, totals=None, col_widths=None):
    body = [header] + rows
    if totals:
        body.append(totals)
    t = Table(body, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]
    if totals:
        style += [
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e0ecff")),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ]
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
    canvas.drawString(20 * mm, 12 * mm, f"Generated {date.today():%Y-%m-%d} · OpenClaw Fitness Bot")
    canvas.drawRightString(190 * mm, 12 * mm, f"Page {doc.page}")
    canvas.setStrokeColor(colors.HexColor("#e5e7eb"))
    canvas.line(20 * mm, 15 * mm, 190 * mm, 15 * mm)
    canvas.restoreState()


# ---- main -----------------------------------------------------------------
def generate_report(data, mode="daily", out="report.pdf"):
    """
    data dict shape (see __main__ for full example):
        user, plan, range_label, summary_line,
        kpis: [(label, value), ...]
        macros: {protein, carbs, fat}
        cal_labels, cal_intake, cal_target
        weight_labels, weights              (weekly only)
        vol_labels, vol_values              (weekly only)
        nutrition: {header, rows, totals}
        workout:   {header, rows}
    """
    S = _styles()
    doc = SimpleDocTemplate(out, pagesize=A4,
                            leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=18 * mm, bottomMargin=20 * mm)
    E = []

    # header
    E.append(Paragraph(f"{data['plan']} — {mode.title()} Report", S["H"]))
    E.append(Paragraph(f"{data['user']} · {data['range_label']}", S["Sub"]))
    E.append(Paragraph(data["summary_line"], S["Sub"]))
    E.append(Spacer(1, 4))
    E.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e5e7eb")))
    E.append(Spacer(1, 8))

    # KPI tiles
    E.append(kpi_row(data["kpis"], S))
    E.append(Spacer(1, 10))

    # charts
    E.append(Paragraph("Overview", S["Sec"]))
    m = data["macros"]
    donut = img(macro_donut(m["protein"], m["carbs"], m["fat"]), 70)
    cals = img(calories_bar(data["cal_labels"], data["cal_intake"], data["cal_target"]), 100)
    top = Table([[donut, cals]], colWidths=[72 * mm, 102 * mm])
    top.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    E.append(top)

    if mode == "weekly":
        E.append(Spacer(1, 6))
        w = img(weight_line(data["weight_labels"], data["weights"]), 82)
        v = img(volume_bar(data["vol_labels"], data["vol_values"]), 82)
        bottom = Table([[w, v]], colWidths=[87 * mm, 87 * mm])
        bottom.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        E.append(bottom)

    # nutrition
    E.append(Paragraph("Nutrition", S["Sec"]))
    n = data["nutrition"]
    E.append(data_table(n["header"], n["rows"], n.get("totals"),
                        col_widths=[60 * mm, 30 * mm, 27 * mm, 27 * mm, 26 * mm]))

    # workout
    E.append(Paragraph("Training", S["Sec"]))
    wo = data["workout"]
    E.append(data_table(wo["header"], wo["rows"],
                        col_widths=[58 * mm, 30 * mm, 30 * mm, 52 * mm]))

    doc.build(E, onFirstPage=_footer, onLaterPages=_footer)
    return out


# ---- demo data ------------------------------------------------------------
if __name__ == "__main__":
    weekly = {
        "user": "Alex R.", "plan": "Lean Cut",
        "range_label": "May 25 – May 31, 2026",
        "summary_line": "Goal: Cut · 1,800 kcal/day target · 4 workouts/week",
        "kpis": [
            ("Avg kcal", "1,765"),
            ("Protein", "148g"),
            ("Workouts", "4/4"),
            ("Weight Δ", "-0.6 kg"),
        ],
        "macros": {"protein": 148, "carbs": 165, "fat": 52},
        "cal_labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "cal_intake": [1720, 1850, 1690, 1810, 1900, 1650, 1730],
        "cal_target": 1800,
        "weight_labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "weights": [78.4, 78.2, 78.1, 77.9, 78.0, 77.8, 77.8],
        "vol_labels": ["Push", "Pull", "Legs", "Full"],
        "vol_values": [22, 20, 24, 16],
        "nutrition": {
            "header": ["Meal", "kcal", "P (g)", "C (g)", "F (g)"],
            "rows": [
                ["Breakfast", "420", "32", "45", "12"],
                ["Lunch", "560", "48", "52", "18"],
                ["Snack", "210", "18", "20", "6"],
                ["Dinner", "575", "50", "48", "16"],
            ],
            "totals": ["Total", "1,765", "148", "165", "52"],
        },
        "workout": {
            "header": ["Exercise", "Sets x Reps", "Load", "Notes"],
            "rows": [
                ["Back Squat", "4 x 6", "90 kg", "RPE 8"],
                ["Bench Press", "4 x 8", "70 kg", "Last set to failure"],
                ["Romanian DL", "3 x 10", "80 kg", ""],
                ["Pull-ups", "3 x max", "BW", "12/10/8"],
            ],
        },
    }
    generate_report(weekly, mode="weekly", out="/home/claude/weekly_demo.pdf")

    daily = dict(weekly)
    daily["range_label"] = "Saturday, May 31, 2026"
    daily["cal_labels"] = ["Breakfast", "Lunch", "Snack", "Dinner"]
    daily["cal_intake"] = [420, 560, 210, 575]
    generate_report(daily, mode="daily", out="/home/claude/daily_demo.pdf")
    print("done")
