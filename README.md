# bnb_pricing

Offline command-line tool that turns an Airbnb host's bookings CSV into a
single **A4 PDF report**: 12 subplots (one per month, last 12 months),
each showing nightly rates as colored bars whose color encodes how far
in advance the booking was made.

No network calls, no accounts, no cloud — runs entirely on the host's machine.

---

## Quick start

```bash
# 1. one-time setup (creates .venv, installs deps)
make setup

# 2. generate a synthetic CSV so you can try it without real data
make sample

# 3. produce the PDF report
make analyze
```

Or without the Makefile:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

.venv/bin/python -m bnb_pricing generate-sample --output sample_bookings.csv
.venv/bin/python -m bnb_pricing analyze --input sample_bookings.csv --output report.pdf
```

Open `report.pdf` in any PDF viewer.

---

## CLI

```
python -m bnb_pricing analyze --input bookings.csv --output report.pdf
                              [--end-month 2026-06] [--config columns.yaml]

python -m bnb_pricing generate-sample [--output sample_bookings.csv]
```

| Flag | Default | Purpose |
|---|---|---|
| `--input`     | (required) | bookings CSV path |
| `--output`    | `report.pdf` | output PDF path |
| `--end-month` | current calendar month | most recent month shown; report covers this month + the 11 before it |
| `--config`    | none | YAML file overriding CSV column names |

---

## Input CSV

Default schema (matches `generate-sample` output):

```
booking_date,checkin,checkout,payout
2026-02-21,2026-03-05,2026-03-08,328
```

* Dates are ISO `YYYY-MM-DD`.
* `payout` is the **total net** payout for the booking; the tool divides by nights internally.
* `checkout` may be replaced by an integer `nights` column — if `checkout` is missing, the tool derives it from `checkin + nights`.

### Different column names? Use a YAML config

```yaml
# columns.yaml
columns:
  checkin:  arrival_date
  checkout: departure_date
  payout:   net_amount
  booking_date: confirmed_at
```

Then: `--config columns.yaml`. Only the keys you want to override need to appear.

### Bad rows

* Unparseable dates → row skipped with a `WARNING` naming the spreadsheet row number.
* `nights < 1` → row skipped with a warning.
* Missing required column → fatal error (`booking_date`, `checkin`, `payout`, and `checkout` *or* `nights`).

---

## What the chart shows

* **3 × 4 grid** of subplots, oldest top-left → newest bottom-right.
* Each subplot's **X axis** = days of that month — **every day from 1 to 28/30/31 is labeled** (rotated 90°) so the host can count exactly how many nights a bar covers.
* Each subplot's **Y axis** = nightly rate (`payout / nights`). **All 12 subplots share the same Y scale** so months are directly comparable.
* Each booking is drawn as a rectangle whose **width = number of nights** and whose **color** encodes the lead time (booking date → check-in). The **exact nightly rate is printed just above each bar** (e.g. a `50` label on top of a 50 €/night bar).

| Color | Lead time |
|---|---|
| red       | ≤ 14 days        |
| orange    | 15 – 30 days     |
| yellow    | 31 – 60 days     |
| light blue| 61 – 90 days     |
| green     | > 90 days        |

A single shared legend at the bottom of the page documents the color scale.

### Stays that cross a month boundary

The stay is **split visually** into one bar per month, each covering only that month's days. Both bars keep the same height and color: lead-time/color is computed **once per booking** from the original `(booking_date, checkin)` pair and applied to every segment.

### Configurability

* Column-name mapping lives in `bnb_pricing/config.py::COLUMN_MAP`. Changing a column name does not touch any other file.
* Color buckets live in `bnb_pricing/config.py::COLOR_BUCKETS`. Add, remove, or recolor a bucket by editing that single list; the legend, color assignment, and rendering all pick the change up automatically.

---

## Design choices

* **Bar primitive** — `matplotlib.patches.Rectangle`. Plain `ax.bar` centers each bar on its X value, making multi-day stays awkward; rectangles let us specify *exact* day-of-month start + width, which matches the data semantics cleanly.
* **X-axis ticks** — every single day of the month is shown (1, 2, 3 … 31), rotated 90°. Sparse ticks are easier to read at a glance but they hide exactly the information the host needs: how many nights a booking lasted. A daily tick grid trades a little label clutter for instant "count the days under the bar" readability.
* **Price labels above bars** — each bar carries its nightly rate as a small numeric label so the host doesn't need to eyeball the Y axis. Whole numbers render without decimals (`50`), otherwise one decimal is shown (`49.5`).
* **Checkout day is not a billed night.** A stay from Jan 30 → Feb 1 is 2 nights (Jan 30, Jan 31). The Feb 1 checkout day is not drawn.
* **Overlapping bookings.** Real Airbnb data should not have overlaps, but if two bookings claim the same day we draw **both rectangles with mild alpha (0.85)** and log a warning. Nothing is silently dropped.
* **Empty months** still render as a labeled, empty subplot — they communicate "we had no bookings" which is information.
* **Backend `Agg`** is forced so the tool works on headless / SSH machines.

---

## Project layout

```
bnb_pricing/
  __init__.py
  __main__.py        # argparse + subcommands
  config.py          # COLUMN_MAP, COLOR_BUCKETS, YAML loader
  loader.py          # CSV -> validated DataFrame
  segments.py        # split stays into per-month rectangles
  chart.py           # build figure, save PDF
  sample.py          # synthetic data generator
tests/
  test_loader.py
  test_segments.py
Makefile
requirements.txt
```

---

## Tests

```bash
make test
```

Covers: bucket boundary days, nightly-rate math, month-boundary split, loader robustness (bad dates, nights<1, missing columns, `nights` fallback).
