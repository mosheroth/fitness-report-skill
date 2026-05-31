# `data` dict schema

This is the input contract for `generate_report(data, mode, out)`. Build this dict from the user's logged food and workouts, then call the function. Every key listed under "Required (all modes)" must be present or the build raises a `KeyError`.

## Required (all modes)

| Key | Type | Notes |
|-----|------|-------|
| `user` | str | Display name, e.g. `"Alex R."` |
| `plan` | str | Plan/program name, e.g. `"Lean Cut"`. Shown in the title. |
| `range_label` | str | Date or date-range string, e.g. `"May 25 – May 31, 2026"` (weekly) or `"Saturday, May 31, 2026"` (daily). Free text — you format it. |
| `summary_line` | str | One-line goal summary under the header, e.g. `"Goal: Cut · 1,800 kcal/day target · 4 workouts/week"` |
| `kpis` | list of `(label, value)` tuples | 3–4 recommended; they share a row, so more than 4 gets cramped. Both label and value are strings. |
| `macros` | dict | `{"protein": int_g, "carbs": int_g, "fat": int_g}` — grams. Drives the donut + center total. |
| `cal_labels` | list[str] | X-axis labels for the calories bar. Weekly: weekday names. Daily: meal names. |
| `cal_intake` | list[number] | Bar heights (kcal), same length as `cal_labels`. |
| `cal_target` | int | Drawn as a dashed target line on the calories chart. |
| `nutrition` | dict | See below. |
| `workout` | dict | See below. |

### `nutrition`
```python
"nutrition": {
    "header": ["Meal", "kcal", "P (g)", "C (g)", "F (g)"],   # 5 columns expected by default widths
    "rows":   [["Breakfast", "420", "32", "45", "12"], ...], # all cells strings
    "totals": ["Total", "1,765", "148", "165", "52"],         # optional; rendered as a highlighted footer row
}
```
`totals` is optional — omit the key to skip the footer row. Keep 5 columns to match the default column widths in `generate_report`; if you change the column count, also adjust the `col_widths` passed to `data_table` in the script.

### `workout`
```python
"workout": {
    "header": ["Exercise", "Sets x Reps", "Load", "Notes"],   # 4 columns expected by default widths
    "rows":   [["Back Squat", "4 x 6", "90 kg", "RPE 8"], ...],
}
```
No totals row for workouts. Keep 4 columns to match default widths.

## Required for `mode="weekly"` only

These power the second chart row (weight trend + training volume). They are ignored in daily mode.

| Key | Type | Notes |
|-----|------|-------|
| `weight_labels` | list[str] | X-axis labels for the weight line (e.g. weekdays or dates). |
| `weights` | list[number] | Bodyweight values (kg), same length as `weight_labels`. |
| `vol_labels` | list[str] | Categories for the training-volume bar (e.g. `["Push","Pull","Legs","Full"]` or muscle groups). |
| `vol_values` | list[number] | Volume per category (e.g. total sets), same length as `vol_labels`. |

## Full weekly example

```python
data = {
    "user": "Alex R.",
    "plan": "Lean Cut",
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
```

## Daily example

Same as above but drop the weekly-only keys and switch the calorie chart to per-meal:

```python
daily = {
    "user": "Alex R.",
    "plan": "Lean Cut",
    "range_label": "Saturday, May 31, 2026",
    "summary_line": "Goal: Cut · 1,800 kcal/day target",
    "kpis": [("Today", "1,765 kcal"), ("Protein", "148g"), ("Workout", "Done"), ("Target", "1,800")],
    "macros": {"protein": 148, "carbs": 165, "fat": 52},
    "cal_labels": ["Breakfast", "Lunch", "Snack", "Dinner"],
    "cal_intake": [420, 560, 210, 575],
    "cal_target": 1800,
    "nutrition": { ... },   # same shape as above
    "workout":   { ... },   # same shape as above
}
generate_report(daily, mode="daily", out="report.pdf")
```

## Tips

- All table cells are strings — format numbers (thousands separators, units) before putting them in. The generator does not format for you.
- List-length mismatches (e.g. `cal_intake` shorter than `cal_labels`) will produce a misaligned chart rather than an error, so validate lengths when building from live data.
- For an empty day (no workout logged), pass a single placeholder row like `["Rest day", "—", "—", "—"]` so the table isn't blank.
