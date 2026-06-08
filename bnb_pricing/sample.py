"""Generate a synthetic sample_bookings.csv for offline testing.

The output is deterministic so test runs and demos look the same every time.
It covers the last 12 months relative to a fixed reference date and
intentionally includes:
  * all five lead-time buckets,
  * single-night and multi-night stays,
  * at least one stay that crosses a month boundary,
  * at least one month with zero bookings.
"""

from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path
from typing import List, NamedTuple


class _Row(NamedTuple):
    booking_date: date
    checkin: date
    checkout: date
    payout: int


# Reference "today" anchoring the 12-month window. We hard-code it so the
# sample file is byte-identical across machines and CI runs.
_REFERENCE_TODAY = date(2026, 6, 8)


def _b(checkin: date, nights: int, lead_days: int, payout: int) -> _Row:
    """Small helper: build a row from checkin + nights + lead time."""
    return _Row(
        booking_date=checkin - timedelta(days=lead_days),
        checkin=checkin,
        checkout=checkin + timedelta(days=nights),
        payout=payout,
    )


def _sample_rows() -> List[_Row]:
    """Hand-curated bookings spanning ~12 months from _REFERENCE_TODAY."""
    return [
        # --- Jul 2025: mix of leads ---
        _b(date(2025, 7, 3),  2,  5,  124),  # red
        _b(date(2025, 7, 12), 3, 22,  210),  # orange
        _b(date(2025, 7, 25), 1, 50,   80),  # yellow

        # --- Aug 2025 ---
        _b(date(2025, 8, 2),  4,  8,  232),  # red
        _b(date(2025, 8, 15), 2, 75,  180),  # light blue
        _b(date(2025, 8, 28), 2, 120, 220),  # green

        # --- Sep 2025 ---
        _b(date(2025, 9, 5),  3, 40,  216),  # yellow
        _b(date(2025, 9, 20), 1, 10,   55),  # red

        # --- Oct 2025 ---
        _b(date(2025, 10, 1),  2, 95,  200),  # green
        _b(date(2025, 10, 18), 5, 28,  340),  # orange

        # --- Nov 2025: deliberately empty ---

        # --- Dec 2025: includes a stay crossing into Jan 2026 ---
        _b(date(2025, 12, 22), 4, 130, 600),  # green
        _b(date(2025, 12, 30), 3,  14, 420),  # red (Dec 30 → Jan 2)

        # --- Jan 2026 ---
        _b(date(2026, 1, 10),  2, 33,  120),  # yellow
        _b(date(2026, 1, 24),  1, 62,   65),  # light blue

        # --- Feb 2026 ---
        _b(date(2026, 2, 7),   3, 18,  210),  # orange
        _b(date(2026, 2, 21),  2,  6,  116),  # red

        # --- Mar 2026 ---
        _b(date(2026, 3, 3),   4, 88,  328),  # light blue
        _b(date(2026, 3, 19),  2, 45,  150),  # yellow

        # --- Apr 2026 ---
        _b(date(2026, 4, 5),   1, 12,   60),  # red
        _b(date(2026, 4, 15),  3, 100, 285),  # green
        _b(date(2026, 4, 28),  2, 29,  136),  # orange

        # --- May 2026 ---
        _b(date(2026, 5, 9),   5, 55,  390),  # yellow
        _b(date(2026, 5, 23),  2, 80,  176),  # light blue

        # --- Jun 2026 ---
        _b(date(2026, 6, 2),   3, 9,   192),  # red
        _b(date(2026, 6, 14),  2, 35,  144),  # orange
        _b(date(2026, 6, 27),  4, 110, 480),  # green
    ]


def write_sample_csv(output_path: Path) -> int:
    """Write the sample CSV to `output_path`. Returns the row count."""
    rows = _sample_rows()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["booking_date", "checkin", "checkout", "payout"])
        for r in rows:
            writer.writerow([
                r.booking_date.isoformat(),
                r.checkin.isoformat(),
                r.checkout.isoformat(),
                r.payout,
            ])
    return len(rows)
