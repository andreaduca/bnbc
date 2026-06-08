PY := .venv/bin/python
PIP := .venv/bin/pip

.PHONY: setup test sample analyze clean

setup:
	python3 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

test:
	$(PY) -m pytest -q

sample:
	$(PY) -m bnb_pricing generate-sample --output sample_bookings.csv

analyze:
	$(PY) -m bnb_pricing analyze --input sample_bookings.csv --output report.pdf

clean:
	rm -f report.pdf sample_bookings.csv
	rm -rf .pytest_cache bnb_pricing/__pycache__ tests/__pycache__
