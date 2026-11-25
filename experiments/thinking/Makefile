# make        rebuild results/ from the data (heavy: about 5 h of Stockfish, then about 10 min)
# make quick  rebuild the chart from results/ (seconds)
HEAVY ?= flock $(abspath ../../.heavy.lock)
PY ?= uv run python

all:
	$(HEAVY) $(PY) sample.py
	$(HEAVY) $(PY) engine.py
	$(PY) analyze.py
	$(MAKE) quick

quick:
	$(PY) chart.py
