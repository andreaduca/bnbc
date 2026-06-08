# bnb_pricing

Offline command-line tool that turns an Airbnb host's bookings CSV into a
single **A4 PDF report**: 12 subplots (one per month, last 12 months),
each showing nightly rates as colored bars whose color encodes how far
in advance the booking was made.

No network calls, no accounts, no cloud — runs entirely on the host's machine.

---

## How to use it

Same flow on Mac and Windows. Steps **1** and **2** are one-time; the rest take seconds. For each new report, just repeat steps **3–5**.

1. **Install Python 3.10 or newer** — go to **https://www.python.org/downloads/** and click the big yellow *Download Python* button. Run the file that downloads.
   *Windows only:* on the installer's first screen, **tick "Add python.exe to PATH"** before clicking *Install Now*. Without this, the launcher cannot find Python.

2. **Put the `bnbc` folder somewhere writable** — your Desktop (Mac) or Documents folder (Windows). Avoid `C:\Program Files\` on Windows; it is write-protected.

3. **Double-click the launcher inside the folder:**
   - **Mac** → `run.command`. *First time only:* if macOS warns about an "unidentified developer", right-click the file → **Open** → **Open**.
   - **Windows** → `run.bat`. *First time only:* if SmartScreen shows *"Windows protected your PC"*, click **More info → Run anyway**.

   First run takes about a minute to install dependencies. Future runs are nearly instant.

4. **Pick your bookings CSV** in the file dialog that appears.

5. **`report.pdf` is written to your Desktop and opens automatically.** Done.

### If it fails

| Symptom | Fix |
|---|---|
| Dialog: *"Python is not installed"* | Repeat step 1. On Windows, re-run the installer and make sure *"Add python.exe to PATH"* is ticked. |
| Dialog: *"Report could not be built"* | Your CSV's columns don't match what's expected — see [Input CSV](#input-csv) below and forward that section to whoever sent you the file. |
| No PDF window opened | It's still on your Desktop as `report.pdf` — double-click it. |

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
* Each subplot's **X axis** = days of that month, with a handful of date markers (1, 8, 15, 22, and the last day of the month) so the chart stays uncluttered. **The number of nights in each booking is shown by the bar itself**: thin white vertical separators inside the colored rectangle split it into one "cell" per night, so the host counts cells (a 3-night bar shows 3 cells separated by 2 white lines).
* Each subplot's **Y axis** = nightly rate (`payout / nights`). **All 12 subplots share the same Y scale** so months are directly comparable.
* Each booking is drawn as a **black-bordered rectangle** (the explicit "this is one booking" cue) whose **width = number of nights** and whose **fill color** encodes the lead time (booking date → check-in). Two consecutive bookings always keep a small empty margin between their black borders, so back-to-back bookings stay visually distinct even when they share color and nightly rate. The **exact nightly rate is printed just above each bar, rotated 90°** (vertical text) so adjacent narrow bars don't have their labels collide.

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
* **Booking grouping** — every booking is wrapped in a thin black border, regardless of how many nights it covers. The border is the unambiguous "one booking" signal: even if two consecutive bookings share color and price, each one has its own black rectangle.
* **Empty margin between bookings** — every booking is inset by a small amount in data space, so two back-to-back booking borders never touch. This margin is the only thing the eye needs to tell "one 5-night booking" from "a 2-night and a 3-night booking back to back".
* **Counting nights inside a booking** — multi-night bookings carry thin white vertical separators inside the colored fill, splitting it into one cell per night. A 1-night booking has zero internal separators and renders as a single colored cell inside its black border.
* **X-axis ticks** — sparse: 1, 8, 15, 22, and the last day of the month. The duration of a stay is now encoded directly in the bar, so labeling every day would be visually noisy and redundant.
* **Price labels above bars (rotated 90°)** — each bar carries its nightly rate as a small numeric label above the booking. Labels are rotated 90° (vertical text) so adjacent narrow bars don't have their labels overlap horizontally. Whole numbers render without decimals (`50`), otherwise one decimal is shown (`49.5`).
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
run.command          # double-clickable launcher (macOS)
run.bat              # double-clickable launcher (Windows)
Makefile
requirements.txt
```

---

## Tests

```bash
make test
```

Covers: bucket boundary days, nightly-rate math, month-boundary split, loader robustness (bad dates, nights<1, missing columns, `nights` fallback).

---

## Using the chart to set better prices

### What to read off the chart

* **Color mix per month** = your lead-time profile. Lots of green / light blue means early bookers love this month — you have pricing power here. All red means people only book you reactively, close to the date.
* **Bar heights vs colors within a month** = are you actually charging early bookers more? Green bars *taller* than red bars = working as intended. Green *shorter* than red = you accidentally rewarded early commitment with a discount.
* **Empty stretches** = unsold inventory. Empty months mean either zero demand or you priced yourself out of the market. Empty *gaps between bookings* are opportunities to fill with a targeted discount.
* **Cross-month comparison** (the shared Y axis is why) = seasonality. The months that consistently sit higher are your peak; price aggressively there.

### Your strategy: "high early, low last-minute"

> *"Set very high prices 6 months ahead, reduce as the deadline approaches, minimum for last-minute."*

This is the **inverse** of how hotels and airlines price — they start moderate and *raise* toward the date (classic yield management). Both can be correct. Which one wins for *your* apartment depends on **two axes**, not one.

**Axis 1 — Lead time.** Early bookers and last-minute bookers are different segments with different price sensitivities. Treating them as one market is the mistake. Your strategy already accounts for this — just from the opposite direction hotels do.

**Axis 2 — Competitive position of your apartment.** This decides *which direction* the lead-time curve should run.

* **Scarce / unique property** — beachfront house, design loft, the only 4-bedroom in a small town, anything with no real substitute. Demand for *your* place is **inelastic**: guests can't shop around, because nothing comparable exists. Certainty-seekers booking 3-6 months ahead will pay a premium to lock in *your* specific place. **Your strategy fits this case well.** Risk is low: last-minute opportunists fill what's left at a discount, and you face no real competition pulling them away.
* **Commodity property** — one of 50 similar 1-bedrooms in a dense urban market. Demand is **highly elastic**: a $20/night gap sends the guest to a comparable listing next door. **Your strategy backfires here.** Pricing 6 months out at a premium leaves your calendar empty until the last-minute discount kicks in, while flexible guests book your cheaper competitors. **Standard yield management is correct** in this case: start at market rate, hold or *raise* as availability shrinks — because the late bookers (locked-in trip dates, urgent need) are the inelastic segment.
* **Hybrid (most real apartments).** Apply both lenses *per date*. Peak weeks (school holidays, local events, your city's annual festival) behave like a scarce property — hold the premium late. Off-peak weeks behave like a commodity — start moderate, don't overshoot, and drop sooner if velocity is slow.

**Diagnostic from the chart itself**: in a typical month, do bookings cluster in the green / light-blue colors (3+ months out)? Then you have pricing power on that month — your strategy works. If most bookings arrive in red / orange (≤ 30 days out), you're in commodity territory for that month — invert the curve.

**Verdict.** Your strategy is correct **for a scarce property or peak dates**, wrong **for a commodity property or off-peak dates**. Don't pick *one* strategy for the whole calendar — pick one **per month**, based on the chart's color distribution.

### More pricing advice

1. **Price weekends differently.** Fri/Sat are a different product from Mon/Tue — separate them.
2. **Identify peak vs off-peak months from your own data** (this chart is built for that). Hold premium in peak, discount earlier in trough.
3. **For peak dates, don't fear the empty night.** Holding €200/night and renting 80% of the month often beats dropping to €140 and renting 95%.
4. **Use minimum-night requirements** to reduce cleaning overhead per occupied night and capture longer-stay guests, especially in peak.
5. **Fill isolated gaps with targeted discounts.** A lone empty night between two bookings is nearly pure margin if you can drop it 30% and fill it.
6. **One booking is anecdote, the curve is data.** Don't chase outliers — only adjust price when a *pattern* repeats across months.

### How this specific chart helps you

| Chart feature | What it tells you about pricing |
|---|---|
| **Color distribution by month** | Your competitive-position diagnostic. Mostly green/blue → you have pricing power, charge early bookers a premium. Mostly red → you're a commodity, invert the curve. This is the single most important signal on the chart. |
| **Bar height vs color within a month** | Audits whether your current pricing actually rewards early commitment, or accidentally inverts it. |
| **Empty days** | Quantifies vacancy. Multiply by your average rate to see lost revenue at a glance. |
| **Cross-month comparison (shared Y axis)** | Seasonality. Months consistently sitting higher are your peak — apply the scarce-property strategy there even if your "average month" is commodity. |
| **Year-on-year subplots** (once you have 2+ years of data) | Seasonality validation. Patterns that repeat are signal; one-offs are noise. |

---

## Future tools to improve price strategy

> This tool is **strictly offline by design**. Anything below that needs competitor data, live APIs, or web scraping breaks that constraint and would need an explicit "now requires internet" carve-out.

Ranked by **value / complexity ratio** — highest first.

### Tier 1 — High value, low complexity (build these first)

| Tool | What it does | Why it pays off |
|---|---|---|
| **Occupancy rate per month** | Add `% nights booked` to each subplot title. | Quantifies the metric the chart already implies visually. One line of code per subplot, instantly actionable. |
| **Average rate split by weekday vs weekend** | Two-row mini-table per month, or a separate page. | Weekends usually justify a 20-40% premium; most hosts under-price them. |
| **Cumulative monthly revenue with a target line** | Sum payouts per month, draw a horizontal goal line. | Answers "am I on track this month?" without the host doing arithmetic. |
| **Lead-time histogram per month** | Small bar chart: how many bookings landed in each lead-time bucket. | Shows *when* a month historically fills — tells you when to start cutting price for that month next year. |
| **Year-over-year overlay** | When 2+ years of data exist, draw last-year's bars as ghost outlines behind this year's. | The easiest seasonality validation. Removes guesswork from "is this month always slow?" |

### Tier 2 — Medium complexity, still high value

| Tool | What it does | Why it pays off |
|---|---|---|
| **"Missed revenue" detector** | Flag isolated empty nights between bookings; estimate revenue if filled at 70% of average rate. | Identifies the lowest-effort revenue lift on the calendar. |
| **Booking velocity curves** | Cumulative bookings vs days-out-from-arrival, one curve per month. | Shows whether a month is filling faster or slower than usual — triggers a *price* response. |
| **Rule-based price suggestions** | Heuristics like *"if 60 days out and <30% booked, drop 10%; if >80% booked, raise 10%."* | No ML required; codifies the strategy. High value because it removes daily decision fatigue. |

### Tier 3 — Advanced, diminishing returns

| Tool | What it does | Honest take |
|---|---|---|
| **Time-series demand forecasting** | Statistical model predicting next year's bookings/rates. | Worth it only with 3+ years of data. Below that, the model overfits noise. |
| **Price-elasticity optimizer** | Estimate demand-vs-price curve, solve for revenue-maximizing price. | Requires experimentation data — you'd need to actually try prices and observe. Hard without A/B testing. |
| **Competitor pricing comparison** | Pull nearby-listing prices from Airbnb / AirDNA and benchmark. | **Breaks offline constraint.** Useful, but belongs in a separate online tool, not bolted onto this one. |
| **Local event detection** | Cross-reference dates with concerts / conferences / holidays to flag demand spikes. | **Also needs online data.** Same caveat. |

### Bottom line

Build **Tier 1 first**. Occupancy, weekday/weekend, year-over-year are hours of work each for permanent gains in the host's decision-making. **Tier 3 is mostly cargo-cult** unless you have years of data and a real appetite to experiment — the gain over a well-built Tier 1 + Tier 2 stack is small.
