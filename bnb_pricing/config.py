"""Central configuration: column-name mapping and lead-time color buckets.

Every name or threshold the rest of the codebase consults lives here, so
relabelling a CSV column or shifting a color boundary is a one-line change.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml


# --- Column name mapping ---------------------------------------------------
#
# Logical name (left) -> physical column name in the CSV (right).
# `nights` is optional: if `checkout` is missing, we fall back to it.
COLUMN_MAP: Dict[str, str] = {
    "booking_date": "booking_date",
    "checkin": "checkin",
    "checkout": "checkout",
    "payout": "payout",
    "nights": "nights",  # optional fallback when `checkout` is absent
}


# --- Lead-time color buckets ----------------------------------------------
#
# Ordered list of (inclusive upper-bound days, color, human label).
# The last entry's upper_bound is None and acts as the "everything else" bucket.
# Edit this list to add, remove, or recolor buckets — nothing else changes.
@dataclass(frozen=True)
class Bucket:
    upper_bound: Optional[int]  # inclusive; None = no upper bound
    color: str                  # matplotlib-recognized color name or hex
    label: str                  # legend text


COLOR_BUCKETS: List[Bucket] = [
    Bucket(upper_bound=14,   color="#e53935", label="≤ 2 weeks"),       # red
    Bucket(upper_bound=30,   color="#fb8c00", label="2 wk – 1 month"),  # orange
    Bucket(upper_bound=60,   color="#fdd835", label="1 – 2 months"),    # yellow
    Bucket(upper_bound=90,   color="#4fc3f7", label="2 – 3 months"),    # light blue
    Bucket(upper_bound=None, color="#43a047", label="> 3 months"),      # green
]


def bucket_for_lead_days(lead_days: int) -> Bucket:
    """Return the bucket whose range contains `lead_days`.

    Buckets are scanned in order; the first one whose upper bound is >=
    the lead time wins. The trailing bucket has `upper_bound=None` and
    catches anything larger.
    """
    for bucket in COLOR_BUCKETS:
        if bucket.upper_bound is None or lead_days <= bucket.upper_bound:
            return bucket
    # Unreachable because the last bucket has upper_bound=None,
    # but keeps type checkers happy.
    raise RuntimeError("COLOR_BUCKETS must end with an open-ended bucket")


# --- YAML override ---------------------------------------------------------

def load_column_map(yaml_path: Optional[Path]) -> Dict[str, str]:
    """Return COLUMN_MAP, optionally overridden by a YAML file.

    The YAML file should look like::

        columns:
          checkin: arrival_date
          payout: net_amount

    Only the keys you want to override need to appear.
    """
    merged = dict(COLUMN_MAP)
    if yaml_path is None:
        return merged

    if not yaml_path.exists():
        raise FileNotFoundError(f"Config file not found: {yaml_path}")

    with yaml_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    overrides = data.get("columns", {})
    if not isinstance(overrides, dict):
        raise ValueError(
            f"{yaml_path}: top-level 'columns' must be a mapping of "
            "logical-name -> CSV-column-name."
        )

    unknown = set(overrides) - set(COLUMN_MAP)
    if unknown:
        raise ValueError(
            f"{yaml_path}: unknown logical column(s) {sorted(unknown)}. "
            f"Allowed: {sorted(COLUMN_MAP)}."
        )

    merged.update({k: str(v) for k, v in overrides.items()})
    return merged
