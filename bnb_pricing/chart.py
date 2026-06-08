"""Render the 12-subplot A4 PDF report.

Layout: 3 rows x 4 columns, oldest month top-left, newest bottom-right.
All subplots share the same Y scale so months can be compared by eye.
A single shared legend at the bottom maps colors to lead-time buckets.

Bar rendering: we use `matplotlib.patches.Rectangle` for full control
over per-day width and exact day-of-month positioning. See README for
the rationale.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib

# Force a non-interactive backend so the tool works on headless machines.
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Patch
from matplotlib.backends.backend_pdf import PdfPages

from .config import COLOR_BUCKETS
from .segments import Segment


# A4 portrait in inches.
A4_PORTRAIT_INCHES = (8.27, 11.69)

# Each booking's rectangle is shrunk by this many days on each side so two
# back-to-back bookings keep a visible empty margin between their black
# borders — they must never touch even when the second guest checks in
# the same day the first checks out.
_BOOKING_INSET = 0.2

# Thin black border drawn around each booking rectangle. Acts as the
# explicit "this is one booking" grouping cue.
_BOOKING_BORDER_PT = 0.8

# Thin white separators inside a multi-night booking, splitting the
# colored fill into one cell per night.
_CELL_SEPARATOR_PT = 0.6


def build_month_grid(end_month: date) -> List[Tuple[int, int]]:
    """Return the 12 (year, month) pairs ending at `end_month`, oldest first."""
    months: List[Tuple[int, int]] = []
    y, m = end_month.year, end_month.month
    for _ in range(12):
        months.append((y, m))
        # Walk one month back.
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    months.reverse()
    return months


def render_pdf(segments: List[Segment], end_month: date, output_path: Path) -> None:
    """Render the chart described by `segments` into a single-page PDF."""
    months = build_month_grid(end_month)

    # Group segments by (year, month) for O(1) lookup per subplot.
    by_month: Dict[Tuple[int, int], List[Segment]] = {key: [] for key in months}
    for seg in segments:
        key = (seg.year, seg.month)
        if key in by_month:  # silently ignore segments outside the window
            by_month[key].append(seg)

    # Global Y max with ~10% headroom; fall back to 1 so empty data still plots.
    max_rate = max((s.nightly_rate for s in segments), default=0.0)
    y_max = max_rate * 1.10 if max_rate > 0 else 1.0

    fig, axes = plt.subplots(
        nrows=3, ncols=4,
        figsize=A4_PORTRAIT_INCHES,
        sharey=True,
    )
    fig.suptitle("Airbnb nightly rates — last 12 months", fontsize=13, y=0.985)

    for ax, (year, month) in zip(axes.flat, months):
        _draw_month(ax, year, month, by_month[(year, month)], y_max)

    _add_legend(fig)

    # Leave room for the suptitle and bottom legend.
    fig.tight_layout(rect=(0, 0.05, 1, 0.96))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(output_path) as pdf:
        pdf.savefig(fig)
    plt.close(fig)


# --- per-subplot drawing ---------------------------------------------------

def _draw_month(ax, year: int, month: int,
                segs: List[Segment], y_max: float) -> None:
    """Draw one month's subplot. Empty months still get a labeled axis."""
    days_in_month = monthrange(year, month)[1]

    # Each booking is drawn as a black-bordered rectangle (the grouping
    # cue) filled with its lead-time color. For multi-night bookings the
    # fill is split into one cell per night by thin white separators. The
    # _BOOKING_INSET on each side ensures two consecutive booking borders
    # never touch, even when they share a calendar day.
    for seg in segs:
        fill_start = seg.start_day - 0.5 + _BOOKING_INSET
        fill_width = seg.width_days - 2 * _BOOKING_INSET

        rect = Rectangle(
            xy=(fill_start, 0),
            width=fill_width,
            height=seg.nightly_rate,
            facecolor=seg.color,
            edgecolor="black",
            linewidth=_BOOKING_BORDER_PT,
            alpha=0.95,
        )
        ax.add_patch(rect)

        # N-1 equal-width internal separators split the bar into N night
        # cells. A 1-night stay has zero separators (range is empty).
        cell_width = fill_width / seg.width_days
        for k in range(1, seg.width_days):
            ax.vlines(
                x=fill_start + k * cell_width,
                ymin=0,
                ymax=seg.nightly_rate,
                colors="white",
                linewidth=_CELL_SEPARATOR_PT,
            )

        # Price label, rotated 90° so adjacent narrow bars don't have
        # their labels overlap. Anchored just above the bar; the text
        # extends upward.
        center_x = fill_start + fill_width / 2
        ax.text(
            center_x,
            seg.nightly_rate + y_max * 0.015,
            _format_price(seg.nightly_rate),
            ha="center", va="bottom",
            fontsize=5.5,
            rotation=90,
        )

    ax.set_xlim(0.5, days_in_month + 0.5)
    # Headroom for the rotated vertical price labels on top of the
    # tallest bar — they need more vertical room than horizontal labels.
    ax.set_ylim(0, y_max * 1.18)
    ax.set_title(_month_label(year, month), fontsize=9)
    ax.tick_params(axis="both", labelsize=7)

    # Sparse X ticks — the bar itself shows the night count now, so we
    # no longer need a label on every day of the month.
    ax.set_xticks(_sparse_day_ticks(days_in_month))
    ax.grid(axis="y", linestyle=":", linewidth=0.5, alpha=0.6)


def _sparse_day_ticks(days_in_month: int) -> List[int]:
    """Return week-aligned X ticks: 1, 8, 15, 22, plus the last day."""
    ticks = [1, 8, 15, 22]
    if days_in_month not in ticks:
        ticks.append(days_in_month)
    return ticks


def _format_price(value: float) -> str:
    """Render the nightly rate compactly: integer if whole, else 1 decimal."""
    if abs(value - round(value)) < 0.05:
        return f"{int(round(value))}"
    return f"{value:.1f}"


def _month_label(year: int, month: int) -> str:
    return date(year, month, 1).strftime("%b %Y")


def _add_legend(fig) -> None:
    """One shared legend below the grid, one entry per bucket."""
    handles = [Patch(facecolor=b.color, edgecolor="white", label=b.label)
               for b in COLOR_BUCKETS]
    fig.legend(
        handles=handles,
        loc="lower center",
        ncol=len(handles),
        frameon=False,
        fontsize=8,
        title="Lead time (booking-date → check-in)",
        title_fontsize=9,
    )
