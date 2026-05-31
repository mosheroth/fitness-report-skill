# `data` dict schema (planned vs. actual)

Input contract for `generate_report(data, mode, out)`. The bot builds this dict
from the user's plan + logged data, then calls the function.

## LANGUAGE: English only (hard requirement)

All strings in `data` — and therefore everything in the PDF — MUST be English.
The PDF uses ReportLab's built-in Helvetica font, which cannot render Hebrew,
Arabic, or other non-Latin scripts; they show as blank boxes or mirrored text.
The bot must translate/romanize any user-facing text (plan name, workout type
names, workout names, details, notes, KPI labels) to English BEFORE building the
dict. This includes the workout *type* names, which the client chooses freely
(e.g. "Strength", "Core", "Cardio") but must supply in English.

## Showing the future / missing data

The report is built around the user's PLAN, so it shows upcoming days and
scheduled workouts even when nothing has been logged yet:

- Calories: every label in `cal_labels` shows its `cal_planned` bar. The matching
  `cal_actual` entry may be `None` for days not logged — that day still shows the
  plan, and the chart marks it "no data".
- Workouts: every planned workout appears with a status (Done / Planned), so the
  full schedule is visible regardless of completion.

## Required keys (all modes)

| Key | Type | Notes |
|-----|------|-------|
| `user` | str | Display name. English. |
| `plan` | str | Program name, shown in title. English. |
| `range_label` | str | Date or range string you format, e.g. `"May 25 - May 31, 2026"`. |
| `summary_line` | str | One-line goal summary under the header. |
| `kpis` | list of `(label, value)` | 3-4 tiles. Both strings. |
| `cal_labels` | list[str] | X-axis. Weekly: weekday names. Daily: meal names. |
| `cal_planned` | list[number] | Planned intake per label. Same length as `cal_labels`. |
| `cal_actual` | list[number \| None] | Actual intake; use `None` where not logged (shows plan only). Same length as `cal_labels`. |
| `cal_target` | number \| None | Optional dashed reference line. Omit or `None` to hide. |
| `workouts_by_type` | dict | Maps a workout-type name (English, client-chosen) to a list of workout dicts. See below. |

### `workouts_by_type`

```python
"workouts_by_type": {
    "Strength": [                       # <- type name, English, client decides
        {
            "name":   "Lower Body A",   # workout name (English)
            "detail": "Squat, RDL, Lunge",  # short description (English)
            "done":   True,             # bool: completed or not
            "note":   "Felt strong",    # optional free text (English)
        },
        # ... more workouts of this type
    ],
    "Core":   [ ... ],
    "Cardio": [ ... ],
}
```

For each type the report renders:
- a bar in the "Workouts by Type - Planned vs Done" chart (count planned vs count done), and
- a sub-table titled `"<Type> (done/total done)"` with one status-colored row per
  workout: green = done, yellow = planned/not done.

A type with an empty list renders the header plus "No workouts planned."

## Mode differences

`mode` is `"daily"` or `"weekly"` and only affects framing/labels you supply:
- **weekly**: `cal_labels` = weekdays; `workouts_by_type` typically spans the week.
- **daily**: `cal_labels` = meals of the day; `workouts_by_type` is usually that day's session(s).

The function logic is the same; there are no weekly-only required keys anymore.

## Full weekly example

```python
data = {
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
    "cal_actual":  [1720, 1850, 1690, 1810, None, None, None],
    "cal_target":  1800,
    "workouts_by_type": {
        "Strength": [
            {"name": "Lower Body A", "detail": "Squat, RDL, Lunge", "done": True,  "note": "Felt strong"},
            {"name": "Upper Body A", "detail": "Bench, Row, Press",  "done": True,  "note": ""},
        ],
        "Core": [
            {"name": "Core Circuit", "detail": "Plank, Hollow, Leg raise", "done": True,  "note": ""},
            {"name": "Core Circuit", "detail": "Plank, Hollow, Leg raise", "done": False, "note": "Scheduled Sat"},
        ],
        "Cardio": [
            {"name": "Zone 2 Run", "detail": "40 min easy", "done": False, "note": "Scheduled Sun"},
        ],
    },
}
generate_report(data, mode="weekly", out="report.pdf")
```

## Daily example

```python
daily = {
    "user": "Alex R.",
    "plan": "Lean Cut",
    "range_label": "Saturday, May 31, 2026",
    "summary_line": "Goal: Cut - 1,800 kcal/day target",
    "kpis": [("Planned", "1,800"), ("Actual", "1,210"), ("Remaining", "590"), ("Workout", "Planned")],
    "cal_labels":  ["Breakfast", "Lunch", "Snack", "Dinner"],
    "cal_planned": [420, 560, 210, 610],
    "cal_actual":  [420, 560, 230, None],     # dinner not logged yet
    "cal_target":  1800,
    "workouts_by_type": {
        "Strength": [
            {"name": "Lower Body B", "detail": "Deadlift, Split squat", "done": False, "note": "Planned 6pm"},
        ],
    },
}
generate_report(daily, mode="daily", out="report.pdf")
```

## Tips

- All cells/labels are strings (or numbers for the calorie lists) — format numbers
  (units, separators) before passing them in.
- Keep `cal_planned` and `cal_actual` the same length as `cal_labels`. Use `None`
  in `cal_actual` for "not logged yet" rather than `0` (which would look like a
  logged zero-calorie day).
- Workout type names are free text but must be English and are shown verbatim.
