# make        rebuild results/ from the data (heavy, about 3 h: Stockfish takes 2.5 h)
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
