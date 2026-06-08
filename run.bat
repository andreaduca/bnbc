@echo off
REM Double-clickable launcher for non-technical users on Windows.
REM
REM Behaviour:
REM   1. Verifies Python 3.10+ is installed; otherwise opens a dialog with
REM      install instructions and exits.
REM   2. Creates .venv and installs dependencies on first run.
REM   3. Pops up a file picker for the bookings CSV.
REM   4. Writes report.pdf to the Desktop and opens it.

setlocal
cd /d "%~dp0"

REM --- 1. Python check ------------------------------------------------------
where python >nul 2>&1
if errorlevel 1 goto :no_python
python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if errorlevel 1 goto :no_python

REM --- 2. First-run setup ---------------------------------------------------
if not exist .venv (
    echo First-time setup -- about a minute, please wait...
    python -m venv .venv
    .venv\Scripts\python -m pip install --upgrade pip --quiet
    .venv\Scripts\python -m pip install -r requirements.txt --quiet
    echo Setup done.
)

REM --- 3. Ask the user for their bookings CSV ------------------------------
set "CSV_FILE="
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; $d=New-Object System.Windows.Forms.OpenFileDialog; $d.Filter='CSV files (*.csv)|*.csv'; $d.Title='Select your Airbnb bookings file'; if($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK){$d.FileName}"`) do set "CSV_FILE=%%i"

if "%CSV_FILE%"=="" exit /b 0

REM --- 4. Build the report --------------------------------------------------
set "OUTPUT=%USERPROFILE%\Desktop\report.pdf"
echo Building your report...
.venv\Scripts\python -m bnb_pricing analyze --input "%CSV_FILE%" --output "%OUTPUT%"
if errorlevel 1 goto :build_failed

REM --- 5. Open the PDF ------------------------------------------------------
start "" "%OUTPUT%"
exit /b 0


:no_python
powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; $nl=[char]10; $msg='Python 3.10 or newer is not installed on this PC.' + $nl + $nl + '1. Open your browser and go to https://www.python.org/downloads/' + $nl + '2. Click the big yellow Download Python button.' + $nl + '3. Run the file that downloads. IMPORTANT: on the FIRST screen of the installer, tick the box that says ''Add python.exe to PATH''. Then click Install Now.' + $nl + '4. When it finishes, come back here and double-click run.bat again.'; [System.Windows.Forms.MessageBox]::Show($msg, 'Python required', 'OK', 'Error')"
exit /b 1


:build_failed
powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; $msg='Sorry -- the report could not be built. The file you picked may not have the expected columns (booking_date, checkin, checkout, payout). Open the README for the file format, or ask whoever sent you this tool.'; [System.Windows.Forms.MessageBox]::Show($msg, 'Error', 'OK', 'Error')"
exit /b 1
