# make data           download the data (about 19 GB) into data/
# make check          check the shared core against known counts
# make <experiment>   rebuild one experiment from the data
# make quick          rebuild every table, chart and README number from results/ (seconds)
# make all            rebuild everything from the data (hours)

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
