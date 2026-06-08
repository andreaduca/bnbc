"""Command-line entry point: `python -m bnb_pricing ...`.

Subcommands:
  analyze          read a bookings CSV, write a PDF report.
  generate-sample  write a synthetic sample CSV for testing.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path
from typing import Optional

from .chart import render_pdf
from .config import load_column_map
from .loader import BookingDataError, load_bookings
from .segments import split_into_segments
from .sample import write_sample_csv


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m bnb_pricing",
        description="Offline tool that turns an Airbnb bookings CSV into a "
                    "12-month PDF chart of nightly rates and lead times.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- analyze ---
    p_an = sub.add_parser(
        "analyze",
        help="Generate the PDF report from a bookings CSV.",
    )
    p_an.add_argument("--input", required=True, type=Path,
                      help="Path to the input bookings CSV.")
    p_an.add_argument("--output", default=Path("report.pdf"), type=Path,
                      help="Path of the output PDF (default: report.pdf).")
    p_an.add_argument("--end-month", default=None,
                      help="Most recent month shown, format YYYY-MM. "
                           "Defaults to the current calendar month.")
    p_an.add_argument("--config", default=None, type=Path,
                      help="Optional YAML config overriding column names.")

    # --- generate-sample ---
    p_gs = sub.add_parser(
        "generate-sample",
        help="Write a synthetic sample bookings CSV.",
    )
    p_gs.add_argument("--output", default=Path("sample_bookings.csv"), type=Path,
                      help="Path of the sample CSV (default: sample_bookings.csv).")

    return parser


def _parse_end_month(arg: Optional[str]) -> date:
    """Return the first day of the requested end-month, or current month."""
    if arg is None:
        today = date.today()
        return date(today.year, today.month, 1)
    try:
        year_str, month_str = arg.split("-")
        return date(int(year_str), int(month_str), 1)
    except (ValueError, AttributeError) as exc:
        raise SystemExit(
            f"--end-month must be YYYY-MM (got {arg!r}): {exc}"
        ) from exc


def _cmd_analyze(args: argparse.Namespace) -> int:
    column_map = load_column_map(args.config)
    end_month = _parse_end_month(args.end_month)

    try:
        bookings = load_bookings(args.input, column_map)
    except (BookingDataError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if bookings.empty:
        print("WARNING: no valid bookings found after validation.", file=sys.stderr)

    segments = split_into_segments(bookings)
    render_pdf(segments, end_month, args.output)

    print(f"Wrote {args.output} ({len(bookings)} bookings, "
          f"{len(segments)} drawn segments).")
    return 0


def _cmd_generate_sample(args: argparse.Namespace) -> int:
    count = write_sample_csv(args.output)
    print(f"Wrote {count} sample bookings to {args.output}.")
    return 0


def main(argv: Optional[list] = None) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    args = _build_parser().parse_args(argv)

    if args.command == "analyze":
        return _cmd_analyze(args)
    if args.command == "generate-sample":
        return _cmd_generate_sample(args)
    # argparse with required=True prevents this, but keep mypy/readers happy.
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    sys.exit(main())
