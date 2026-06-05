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

- Calories (weekly): every day in the Sun..Sat week shows its planned bar. A day's
  `actual` may be `None` when not logged — that day still shows the plan and is
  marked "no data". Days entirely absent from `cal_days` are auto-filled the same way.
- Workouts: every planned workout appears with a status (Done / Planned), so the
  full schedule is visible regardless of completion.

## Weekly calorie input: dated entries, always Sunday -> Saturday

For `mode="weekly"`, calories are passed as **dated entries**, not parallel lists.
The skill always renders the week as Sunday -> Saturday regardless of the order you
send, and fills any missing days so all seven weekday columns always appear.

```python
"cal_days": [
    {"date": "2026-05-24", "planned": 1800, "actual": 1720},  # Sun
    {"date": "2026-05-25", "planned": 1800, "actual": 1810},  # Mon
    {"date": "2026-05-27", "planned": 1800, "actual": 1690},  # Wed
    {"date": "2026-05-28", "planned": 1800, "actual": None},  # Thu, not logged
    # any order; missing days (e.g. Fri/Sat) are auto-filled planned=0, actual=None
],
"week_of": "2026-05-24",   # OPTIONAL "YYYY-MM-DD"; picks which week to show.
                            # If omitted, the week containing the earliest date is used.
```

- `date`: ISO `"YYYY-MM-DD"` string (or a `datetime.date`). Used to place the entry
  on the correct weekday and to sort Sunday-first.
- `planned`: planned intake for that day (number).
- `actual`: actual logged intake, or `None` if not logged yet (shows plan + "no data").
- Day labels on the chart are derived automatically (Sun, Mon, ... Sat) — you do not
  pass labels for weekly mode.
- Missing days are filled with `planned=0, actual=None`. If you want a real planned
  value shown for a future day, include that day in `cal_days` with its planned number
  and `actual=None`.

For `mode="daily"`, dates do not apply (meals, not days), so daily keeps the simple
parallel lists: `cal_labels`, `cal_planned`, `cal_actual` (see the daily example).

## Required keys (all modes)

| Key | Type | Notes |
|-----|------|-------|
| `user` | str | Display name. English. |
| `plan` | str | Program name, shown in title. English. |
| `range_label` | str | Date or range string you format, e.g. `"May 25 - May 31, 2026"`. |
| `summary_line` | str | One-line goal summary under the header. |
| `kpis` | list of `(label, value)` | 3-4 tiles. Both strings. |
| `cal_target` | number \| None | Optional dashed reference line. Omit or `None` to hide. |
| *calories* | — | Weekly: `cal_days` (+ optional `week_of`). Daily: `cal_labels`, `cal_planned`, `cal_actual`. See the calorie section above. |
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


## Overall progress gauges (replaces the per-type bar chart)

The report shows two semicircular gauges side by side, computed automatically:

- **Workouts completed** — done vs planned across all `workouts_by_type`
  (center shows `done/planned`, e.g. `3/5`).
- **Calorie adherence** — sum of actual vs sum of planned, counting only days that
  have a logged `actual` (center shows a percentage). Color: green >= 90%,
  amber 60-89%, red < 60%.

These are derived from data you already pass; no extra keys are required for them.

## Day-by-day detail (optional `days`)

To include a per-day breakdown of workouts done and food eaten, pass a `days` list.
It renders on its own page after the schedule. Each entry:

```python
"days": [
    {
        "label": "Sunday, May 24",           # English, you format it
        "workouts": [                          # same workout dict shape as elsewhere
            {"name": "Lower Body A", "detail": "Squat, RDL, Lunge",
             "done": True, "note": "Felt strong"},
        ],
        "foods": [                             # what was eaten that day
            {"name": "Oats with berries", "kcal": 420, "protein": 18, "carbs": 62, "fat": 10},
            {"name": "Chicken rice bowl", "kcal": 560, "protein": 45, "carbs": 55, "fat": 16},
        ],
    },
    # ... one entry per day you want to show
]
```

- `label`: free text day heading (English).
- `workouts`: list of the usual workout dicts (`name`, `detail`, `done`, `note`);
  rendered as a status-colored table. Empty list -> "No workouts."
- `foods`: list of `{"name", "kcal", "protein", "carbs", "fat"}`. Macros are grams.
  Any numeric field may be omitted/None (shows "-"); a totals row sums what's present.
  Empty list -> "No food logged."
- `days` is optional and is the same for daily and weekly mode. Omit it to skip the
  per-day section entirely.

## Mode differences

`mode` is `"daily"` or `"weekly"` and only affects framing/labels you supply:
- **weekly**: calories via `cal_days` (dated), always rendered Sunday..Saturday;
  `workouts_by_type` typically spans the week.
- **daily**: calories via `cal_labels`/`cal_planned`/`cal_actual` (meals of the day);
  `workouts_by_type` is usually that day's session(s).

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
    "cal_days": [   # any order; missing days auto-filled; rendered Sun..Sat
        {"date": "2026-05-24", "planned": 1800, "actual": 1720},
        {"date": "2026-05-25", "planned": 1800, "actual": 1810},
        {"date": "2026-05-26", "planned": 1800, "actual": 1850},
        {"date": "2026-05-27", "planned": 1800, "actual": 1690},
        {"date": "2026-05-28", "planned": 1800, "actual": None},
    ],
    "week_of": "2026-05-24",   # optional
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
- Daily mode: keep `cal_planned` and `cal_actual` the same length as `cal_labels`.
  Use `None` (not `0`) for "not logged yet".
- Weekly mode: you don't pass labels; weekday labels are derived from the dates and
  the week is always Sunday..Saturday.
- Workout type names are free text but must be English and are shown verbatim.
