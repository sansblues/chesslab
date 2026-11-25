# make        rebuild results/ from the data (heavy, about 2.5 h: Stockfish takes 2 h)
# make quick  rebuild the chart from results/ (seconds)
HEAVY ?= flock $(abspath ../../.heavy.lock)
PY ?= uv run python -I

.PHONY: all quick

all:
	$(HEAVY) $(PY) extract.py
	$(HEAVY) $(PY) evaluate.py
	$(HEAVY) $(PY) analyze.py
	$(MAKE) quick

quick:
	$(PY) chart.py
