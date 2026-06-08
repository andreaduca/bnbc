"""Split bookings into per-month drawable segments.

A booking that crosses a month boundary needs to appear in each month's
subplot as a separate bar covering only the days inside that month. The
bar's height (nightly rate) and color (lead-time bucket) stay the same —
they are computed once per booking and shared by every segment.
"""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, List

import pandas as pd


@dataclass(frozen=True)
class Segment:
    """One drawable bar inside one month's subplot."""
    year: int
    month: int
    start_day: int   # 1-based, inclusive
    end_day: int     # 1-based, inclusive (start_day + width - 1)
    nightly_rate: float
    color: str

    @property
    def width_days(self) -> int:
        return self.end_day - self.start_day + 1


def split_into_segments(bookings: pd.DataFrame) -> List[Segment]:
    """Convert each booking row into one Segment per month it touches.

    A booking is considered to occupy nights from `checkin` (inclusive)
    through `checkout - 1 day` (inclusive) — i.e. checkout day itself is
    not a billed night. So a 3-night stay spans exactly 3 calendar days.
    """
    segments: List[Segment] = []
    for row in bookings.itertuples(index=False):
        last_night = (row.checkout - pd.Timedelta(days=1)).date()
        segments.extend(_segments_for_stay(
            first_night=row.checkin.date(),
            last_night=last_night,
            nightly_rate=float(row.nightly_rate),
            color=row.color,
        ))
    return segments


def _segments_for_stay(
    first_night: date,
    last_night: date,
    nightly_rate: float,
    color: str,
) -> Iterable[Segment]:
    """Walk month-by-month over [first_night, last_night] and yield Segments."""
    cursor = first_night
    while cursor <= last_night:
        # Last day of `cursor`'s month.
        days_in_month = monthrange(cursor.year, cursor.month)[1]
        month_end = date(cursor.year, cursor.month, days_in_month)

        # This segment ends at the earlier of: stay's last night, month's last day.
        seg_end = min(month_end, last_night)

        yield Segment(
            year=cursor.year,
            month=cursor.month,
            start_day=cursor.day,
            end_day=seg_end.day,
            nightly_rate=nightly_rate,
            color=color,
        )

        # Jump to first day of next month.
        cursor = seg_end + timedelta(days=1)
