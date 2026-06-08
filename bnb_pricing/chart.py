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

    # Slight transparency so neighbouring bars are visually distinct even
    # if the data accidentally overlaps.
    for seg in segs:
        rect = Rectangle(
            xy=(seg.start_day - 0.5, 0),
            width=seg.width_days,
            height=seg.nightly_rate,
            facecolor=seg.color,
            edgecolor="white",
            linewidth=0.5,
            alpha=0.85,
        )
        ax.add_patch(rect)

        # Price label centered above the bar so the host can read it at a glance.
        center_x = seg.start_day - 0.5 + seg.width_days / 2
        ax.text(
            center_x,
            seg.nightly_rate + y_max * 0.01,
            _format_price(seg.nightly_rate),
            ha="center", va="bottom",
            fontsize=5.5,
        )

    ax.set_xlim(0.5, days_in_month + 0.5)
    # Headroom for the price labels sitting on top of the tallest bar.
    ax.set_ylim(0, y_max * 1.08)
    ax.set_title(_month_label(year, month), fontsize=9)
    ax.tick_params(axis="both", labelsize=5)

    # Tick every day of the month so the host can see exactly how many
    # nights each bar covers. Rotate so the labels stay legible.
    ax.set_xticks(range(1, days_in_month + 1))
    ax.tick_params(axis="x", rotation=90, pad=1)
    ax.grid(axis="y", linestyle=":", linewidth=0.5, alpha=0.6)


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
