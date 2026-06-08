"""Load a bookings CSV into a clean, computed DataFrame.

Responsibilities:
  * read the CSV with the configured column names,
  * parse dates permissively but loudly,
  * derive `checkout` from `nights` when needed,
  * compute `nights`, `nightly_rate`, `lead_days`, and the color bucket,
  * skip (with a warning) rows that fail validation rather than crashing.

The returned DataFrame is the single source of truth consumed by
`segments.py` and `chart.py`.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List

import pandas as pd

from .config import Bucket, bucket_for_lead_days


log = logging.getLogger(__name__)


# Logical column names we work with downstream. They live in this module so
# that the loader is the only place that touches CSV-specific names.
_LOGICAL_REQUIRED = ("booking_date", "checkin", "payout")


class BookingDataError(ValueError):
    """Raised when the CSV is structurally unusable (missing required columns)."""


def load_bookings(csv_path: Path, column_map: Dict[str, str]) -> pd.DataFrame:
    """Read `csv_path` and return a validated, enriched DataFrame.

    Returned columns (always present, always named logically):
      booking_date, checkin, checkout, payout, nights,
      nightly_rate, lead_days, color, bucket_label.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {csv_path}")

    raw = pd.read_csv(csv_path)

    # 1) Verify required physical columns exist.
    _check_required_columns(raw, column_map, csv_path)

    # 2) Build a logical-name view of the dataframe. From here on
    #    we never touch the original column names again.
    df = _rename_to_logical(raw, column_map)

    # 3) Parse dates row-by-row so we can name offending rows clearly,
    #    then drop the rows that failed.
    df = _parse_dates(df)

    # 4) Derive checkout from nights when checkout is missing/blank.
    df = _fill_checkout_from_nights(df)

    # 5) Compute nights and drop rows where nights < 1.
    df = _compute_nights(df)

    # 6) Compute payout-derived and lead-time-derived columns.
    df["nightly_rate"] = df["payout"] / df["nights"]
    df["lead_days"] = (df["checkin"] - df["booking_date"]).dt.days

    # 7) Attach bucket color + label (computed once per booking).
    buckets: List[Bucket] = [bucket_for_lead_days(int(d)) for d in df["lead_days"]]
    df["color"] = [b.color for b in buckets]
    df["bucket_label"] = [b.label for b in buckets]

    return df.reset_index(drop=True)


# --- helpers ---------------------------------------------------------------

def _check_required_columns(
    raw: pd.DataFrame, column_map: Dict[str, str], csv_path: Path
) -> None:
    """Fail fast if the CSV is missing booking_date / checkin / payout."""
    missing = []
    for logical in _LOGICAL_REQUIRED:
        physical = column_map[logical]
        if physical not in raw.columns:
            missing.append(f"{logical!r} (expected CSV column {physical!r})")

    # checkout OR nights must be present; otherwise we cannot derive stays.
    checkout_col = column_map["checkout"]
    nights_col = column_map["nights"]
    if checkout_col not in raw.columns and nights_col not in raw.columns:
        missing.append(
            f"either 'checkout' (CSV column {checkout_col!r}) "
            f"or 'nights' (CSV column {nights_col!r})"
        )

    if missing:
        raise BookingDataError(
            f"{csv_path}: missing required column(s): " + "; ".join(missing)
        )


def _rename_to_logical(raw: pd.DataFrame, column_map: Dict[str, str]) -> pd.DataFrame:
    """Return a copy of `raw` whose columns use our logical names."""
    # Build {physical: logical} only for columns actually present.
    rename = {column_map[logical]: logical
              for logical in column_map
              if column_map[logical] in raw.columns}
    df = raw.rename(columns=rename).copy()

    # Keep only columns we care about (drops noise like ids, notes...).
    keep = [c for c in ("booking_date", "checkin", "checkout", "payout", "nights")
            if c in df.columns]
    return df[keep]


def _parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Parse date columns; warn on bad rows and drop them."""
    date_cols = [c for c in ("booking_date", "checkin", "checkout") if c in df.columns]
    for col in date_cols:
        # `format="mixed"` keeps parsing permissive without pandas warning
        # when some rows fail (their cells become NaT below).
        df[col] = pd.to_datetime(df[col], errors="coerce", format="mixed")

    # Identify rows where any required date failed to parse.
    required_dates = [c for c in ("booking_date", "checkin") if c in df.columns]
    bad_mask = df[required_dates].isna().any(axis=1)
    for idx in df.index[bad_mask]:
        # +2 = 1-based + header row, matches what users see in a spreadsheet.
        log.warning("Row %d: unparseable date(s); skipping.", idx + 2)
    return df.loc[~bad_mask].copy()


def _fill_checkout_from_nights(df: pd.DataFrame) -> pd.DataFrame:
    """If `checkout` is missing or NaT for a row, derive it from `nights`."""
    if "checkout" not in df.columns:
        df["checkout"] = pd.NaT

    if "nights" in df.columns:
        needs_fill = df["checkout"].isna() & df["nights"].notna()
        df.loc[needs_fill, "checkout"] = (
            df.loc[needs_fill, "checkin"]
            + pd.to_timedelta(df.loc[needs_fill, "nights"].astype(int), unit="D")
        )

    # Drop rows still missing a checkout — we cannot draw a stay without one.
    bad_mask = df["checkout"].isna()
    for idx in df.index[bad_mask]:
        log.warning("Row %d: missing checkout and no nights fallback; skipping.",
                    idx + 2)
    return df.loc[~bad_mask].copy()


def _compute_nights(df: pd.DataFrame) -> pd.DataFrame:
    """(Re)compute nights from checkin/checkout; drop nights < 1 rows."""
    df["nights"] = (df["checkout"] - df["checkin"]).dt.days.astype("Int64")

    bad_mask = df["nights"].isna() | (df["nights"] < 1)
    for idx in df.index[bad_mask]:
        log.warning(
            "Row %d: nights=%s is invalid (must be >= 1); skipping.",
            idx + 2, df.at[idx, "nights"],
        )
    df = df.loc[~bad_mask].copy()
    df["nights"] = df["nights"].astype(int)
    return df
