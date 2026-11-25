# chesslab

Tiny experiments in chess.

### [Where are chess games won and lost?](experiments/decided)

Most games are lost to plain mistakes, but the clock's share of the points lost grows with rating,
to 55% for 2400+ players over the board.

[![The clock's share of decisive points lost grows with rating](experiments/decided/decided.svg)](experiments/decided)

### [What is clock time at move 20 worth?](experiments/clock)

In classical chess, 10% more clock at move 20 goes with 1.1 more points per 100 games, and 1.9 for
players who are habitually short of time.

[![Extra clock at move 20 is worth most when little is left](experiments/clock/clock.svg)](experiments/clock)

### [Do textbook endgame rules hold under perfect play?](experiments/endgames)

Mostly, but not at their edges: at sum 5 the rule of five says draw, yet 62% of the positions are
wins.

[![At sum 5 the rule of five says draw, yet 62% of positions are wins](experiments/endgames/endgames.svg)](experiments/endgames)

### [Does thinking at the right moments make you better?](experiments/thinking)

Players who spend their time where it matters most do not gain more rating the next year:
+0.18 Elo per SD (95% CI −1.84 to +2.21).

[![Time allocation does not predict rating change; errors do](experiments/thinking/thinking.svg)](experiments/thinking)

### [Can statistics catch a chess cheater?](experiments/cheating)

Honest players differ by 0.24 mistakes per game, so a cheater who removes fewer than 0.9 per game
is flagged less than half the time.

[![Search 10,000 games and 59% of honest players look like cheaters](experiments/cheating/cheating.svg)](experiments/cheating)

## Run it

You need Linux on x86-64, [uv](https://docs.astral.sh/uv/), make, flock and a C compiler with OpenMP.

```sh
make quick    # rebuild every chart from results/ (seconds)
make data     # download the data into data/ (about 19 GB, once)
make check    # check the shared code against known counts (about 7 min)
make all      # rerun every experiment from the data (about 8 h on 12 cores, 1 GB more disk)
make decided  # rerun one experiment: decided, clock, endgames, thinking or cheating
```

## Layout

```
chesslab/       shared code: games, samples, tablebases, engine, charts, data download
experiments/    one folder per experiment: README, code, results/ and the chart
fathom/         Fathom, a Syzygy probing library in C (MIT license)
data/           downloads and intermediate files (not in git)
```

## Data

- [Lichess open database](https://database.lichess.org): rated games of Oct 2026 (CC0).
- [Lichess broadcasts](https://database.lichess.org): over-the-board games, Jul 2024 to
  Oct 2026 (CC BY-SA 4.0).
- [FIDE rating lists](https://ratings.fide.com), Jul 2023 to Nov 2026.
- [Syzygy tablebases](https://tablebase.lichess.ovh/tables/standard): the WDL tables (win, draw,
  loss) of all 3-5 piece endings and of 60 six-piece ones.
- [Stockfish 19](https://stockfishchess.org) (GPL-3.0).

## License

GPL-3.0-or-later. The files in `fathom/` keep their MIT license.
