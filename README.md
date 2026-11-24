# chesslab

Tiny experiments in chess.

Five small studies on public data: Lichess games, over-the-board games relayed on Lichess,
FIDE rating lists, Syzygy tablebases and Stockfish. The gallery of results comes soon.

## Reproduce

You need Linux on x86-64, [uv](https://docs.astral.sh/uv/), make, flock and a C compiler with OpenMP.

```sh
make data    # download the data into data/ (about 19 GB)
make check   # check the shared code against known counts
make quick   # rebuild every table and chart from the stored results (seconds)
make all     # rebuild everything from the data (hours)
```

## Layout

```
chesslab/       shared code: games, samples, tablebases, engine, charts, data download
fathom/         Fathom, a Syzygy probing library in C (MIT license)
experiments/    one folder per experiment
data/           downloads and caches (not in git)
```

## License

GPL-3.0-or-later. The files in `fathom/` keep their MIT license.
