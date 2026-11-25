# make data           download the data into data/ (about 19 GB, once)
# make check          check the shared core against known counts (about 7 min)
# make quick          rebuild every chart from results/ (seconds)
# make all            rerun every experiment from the data (about 8 h)
# make <experiment>   rerun one: decided, clock, endgames, thinking or cheating

EXPERIMENTS := $(patsubst experiments/%/Makefile,%,$(wildcard experiments/*/Makefile))
HEAVY := flock $(CURDIR)/.heavy.lock
PY := uv run python
export HEAVY PY

.PHONY: quick all data check $(EXPERIMENTS)

quick:
	for e in $(EXPERIMENTS); do $(MAKE) -C experiments/$$e quick || exit 1; done

all: data build/fathom.so $(EXPERIMENTS)

data:
	$(PY) -m chesslab.data

check: build/fathom.so
	$(HEAVY) $(PY) -m chesslab.check

$(EXPERIMENTS): build/fathom.so
	$(MAKE) -C experiments/$@

build/fathom.so: chesslab/fathom.c $(wildcard fathom/*)
	mkdir -p build
	$(CC) -O2 -march=native -fopenmp -fPIC -shared -Ifathom -o $@ $<
