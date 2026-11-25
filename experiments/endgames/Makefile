# make         rebuild results/ from the tablebases and games (heavy, about 50 min)
# make slices  build the C part of the checker (once)
HEAVY ?= flock $(abspath ../../.heavy.lock)
PY ?= uv run python
SLICES := ../../data/endgames/slices.so

all: slices
	$(HEAVY) $(PY) krppkr.py
	$(HEAVY) $(PY) krpkr.py
	$(PY) kpk.py

slices: $(SLICES)

$(SLICES): slices.c
	mkdir -p $(dir $@)
	$(CC) -O2 -march=native -fopenmp -fPIC -shared -I../../fathom -o $@ $<

.PHONY: all slices
