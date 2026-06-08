"""Tests for the CSV loader: bucket edges, nightly rate, robustness."""

from __future__ import annotations

from pathlib import Path

import pytest

from bnb_pricing.config import COLUMN_MAP, bucket_for_lead_days
from bnb_pricing.loader import BookingDataError, load_bookings


# --- Bucket edges ----------------------------------------------------------

@pytest.mark.parametrize("lead_days,expected_label", [
    (0,  "≤ 2 weeks"),
    (14, "≤ 2 weeks"),
    (15, "2 wk – 1 month"),
    (30, "2 wk – 1 month"),
    (31, "1 – 2 months"),
    (60, "1 – 2 months"),
    (61, "2 – 3 months"),
    (90, "2 – 3 months"),
    (91, "> 3 months"),
    (365, "> 3 months"),
])
def test_bucket_edges(lead_days: int, expected_label: str) -> None:
    """Boundary days must land in the bucket the plan specifies."""
    assert bucket_for_lead_days(lead_days).label == expected_label


# --- Nightly rate ----------------------------------------------------------

def test_nightly_rate_is_payout_per_night(tmp_path: Path) -> None:
    """payout 100 over 2 nights -> nightly_rate 50."""
    csv_path = tmp_path / "bookings.csv"
    csv_path.write_text(
        "booking_date,checkin,checkout,payout\n"
        "2026-01-01,2026-02-01,2026-02-03,100\n"
    )
    df = load_bookings(csv_path, COLUMN_MAP)
    assert len(df) == 1
    assert df.loc[0, "nights"] == 2
    assert df.loc[0, "nightly_rate"] == 50.0


# --- Loader robustness -----------------------------------------------------

def test_loader_skips_invalid_nights_and_bad_dates(tmp_path: Path, caplog) -> None:
    """Rows with nights<1 or unparseable dates are skipped, not fatal."""
    csv_path = tmp_path / "bookings.csv"
    csv_path.write_text(
        "booking_date,checkin,checkout,payout\n"
        "2026-01-01,2026-02-01,2026-02-03,100\n"   # ok
        "2026-01-01,2026-02-05,2026-02-05,80\n"    # nights=0 -> skipped
        "2026-01-01,not-a-date,2026-02-10,90\n"    # bad date -> skipped
    )
    df = load_bookings(csv_path, COLUMN_MAP)
    assert len(df) == 1
    assert df.loc[0, "payout"] == 100


def test_loader_falls_back_to_nights_column(tmp_path: Path) -> None:
    """If checkout column is absent, derive it from a `nights` column."""
    csv_path = tmp_path / "bookings.csv"
    csv_path.write_text(
        "booking_date,checkin,nights,payout\n"
        "2026-01-01,2026-02-01,3,300\n"
    )
    df = load_bookings(csv_path, COLUMN_MAP)
    assert df.loc[0, "nights"] == 3
    assert df.loc[0, "nightly_rate"] == 100.0


def test_loader_raises_when_required_columns_missing(tmp_path: Path) -> None:
    """Missing required columns is a fatal, clearly-named error."""
    csv_path = tmp_path / "bookings.csv"
    csv_path.write_text("checkin,checkout,payout\n2026-02-01,2026-02-03,100\n")
    with pytest.raises(BookingDataError) as exc:
        load_bookings(csv_path, COLUMN_MAP)
    assert "booking_date" in str(exc.value)
