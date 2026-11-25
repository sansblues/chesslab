# make        rebuild results/ from the data (heavy, about 30 min)
# make quick  rebuild the chart from results/ (seconds)
HEAVY ?= flock $(abspath ../../.heavy.lock)
PY ?= uv run python

all:
	$(HEAVY) $(PY) extract.py
	$(HEAVY) $(PY) analyze.py
	$(HEAVY) $(PY) recheck.py
	$(MAKE) quick

quick:
	$(PY) chart.py
