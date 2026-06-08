#!/usr/bin/env bash
# Double-clickable launcher for non-technical users.
#
# Behaviour:
#   1. Verifies Python 3.10+ is installed; otherwise opens a dialog with
#      install instructions and exits.
#   2. Creates .venv and installs dependencies on first run.
#   3. Pops up a file picker for the bookings CSV.
#   4. Writes report.pdf to the Desktop and opens it.

set -e
cd "$(dirname "$0")"

dialog() {
    # $1 = message, $2 = icon (stop / caution / note)
    /usr/bin/osascript -e "display dialog \"$1\" buttons {\"OK\"} default button \"OK\" with icon $2" >/dev/null 2>&1 || true
}

# --- 1. Python check ------------------------------------------------------
if ! command -v python3 >/dev/null 2>&1 \
    || ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    dialog "Python 3.10 or newer is not installed on this Mac.\n\n1. Open Safari and go to:\n   https://www.python.org/downloads/\n\n2. Click the big yellow 'Download Python' button.\n\n3. Open the file that downloads (its name ends in .pkg) and click Continue, Continue, Install.\n\n4. When that finishes, come back here and double-click run.command again." stop
    exit 1
fi

# --- 2. First-run setup ---------------------------------------------------
if [ ! -d .venv ]; then
    echo "First-time setup — this takes about a minute, please wait..."
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip --quiet
    .venv/bin/pip install -r requirements.txt --quiet
    echo "Setup done."
fi

# --- 3. Ask the user for their bookings CSV -------------------------------
CSV_FILE=$(/usr/bin/osascript -e 'POSIX path of (choose file with prompt "Select your Airbnb bookings file (CSV)" of type {"csv"})' 2>/dev/null) || {
    # User clicked Cancel.
    exit 0
}

# --- 4. Build the report --------------------------------------------------
OUTPUT="$HOME/Desktop/report.pdf"
echo "Building your report..."

if ! .venv/bin/python -m bnb_pricing analyze --input "$CSV_FILE" --output "$OUTPUT"; then
    dialog "Sorry — the report could not be built. The file you picked may not have the expected columns (booking_date, checkin, checkout, payout). Open the README for the file format, or ask whoever sent you this tool." stop
    exit 1
fi

# --- 5. Open the PDF ------------------------------------------------------
open "$OUTPUT"
