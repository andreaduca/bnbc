"""Tests for the month-splitting logic in segments.py."""

from __future__ import annotations

import pandas as pd

from bnb_pricing.segments import split_into_segments


def _one_booking_df(checkin: str, checkout: str, nightly_rate: float,
                    color: str = "#000000") -> pd.DataFrame:
    """Build a one-row DataFrame mirroring loader.load_bookings's output."""
    return pd.DataFrame([{
        "booking_date": pd.Timestamp("2025-01-01"),
        "checkin": pd.Timestamp(checkin),
        "checkout": pd.Timestamp(checkout),
        "payout": nightly_rate,            # not used by segments
        "nights": 0,                       # not used by segments
        "nightly_rate": nightly_rate,
        "lead_days": 30,                   # not used by segments
        "color": color,
        "bucket_label": "x",
    }])


def test_single_month_stay_produces_one_segment() -> None:
    df = _one_booking_df("2026-03-10", "2026-03-13", 75.0)
    segs = split_into_segments(df)

    assert len(segs) == 1
    seg = segs[0]
    assert (seg.year, seg.month) == (2026, 3)
    assert seg.start_day == 10
    assert seg.end_day == 12          # checkout day is not a billed night
    assert seg.width_days == 3
    assert seg.nightly_rate == 75.0


def test_month_boundary_stay_is_split() -> None:
    """Jan 30 -> Feb 2 yields Jan 30-31 and Feb 1, same height + color."""
    df = _one_booking_df("2026-01-30", "2026-02-02", 50.0, color="#abcdef")
    segs = sorted(split_into_segments(df), key=lambda s: (s.year, s.month))

    assert len(segs) == 2
    jan, feb = segs

    assert (jan.year, jan.month, jan.start_day, jan.end_day) == (2026, 1, 30, 31)
    assert (feb.year, feb.month, feb.start_day, feb.end_day) == (2026, 2, 1, 1)

    # Both segments share the same height and color.
    assert jan.nightly_rate == feb.nightly_rate == 50.0
    assert jan.color == feb.color == "#abcdef"


def test_stay_spanning_three_months_yields_three_segments() -> None:
    """A long stay correctly fans out across every month it touches."""
    df = _one_booking_df("2026-01-30", "2026-03-02", 100.0)
    segs = sorted(split_into_segments(df), key=lambda s: (s.year, s.month))

    assert [(s.year, s.month) for s in segs] == [(2026, 1), (2026, 2), (2026, 3)]
    assert segs[0].start_day == 30 and segs[0].end_day == 31    # Jan 30-31
    assert segs[1].start_day == 1  and segs[1].end_day == 28    # all of Feb
    assert segs[2].start_day == 1  and segs[2].end_day == 1     # Mar 1
