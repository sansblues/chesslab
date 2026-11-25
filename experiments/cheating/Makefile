# make        rebuild results/ from the data (heavy, about 3 min)
# make quick  rebuild the chart from results/ (seconds)
HEAVY ?= flock $(abspath ../../.heavy.lock)
PY ?= uv run python

all:
	$(HEAVY) $(PY) extract.py
	$(PY) analyze.py
	$(MAKE) quick

quick:
	$(PY) chart.py
