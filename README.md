# chesslab

Tiny experiments in chess.

### [Where are chess games won and lost?](experiments/decided)

Mostly to plain mistakes. But the higher the rating, the more the clock decides: over the board at
2400+, it costs 55% of the points lost.

[![The clock's share of the points lost: online and over the board, by rating](experiments/decided/decided.svg)](experiments/decided)

### [Does more clock at move 20 go with better results?](experiments/clock)

Yes, a little. 10% more clock at move 20 goes with about 1 point more per 100 classical games, and 2
for players who are often short of time.

[![Points per 100 games with 10% more clock, by clock left at move 20](experiments/clock/clock.svg)](experiments/clock)

### [Do textbook endgame rules hold under perfect play?](experiments/endgames)

Mostly, but not at the edges. The rule of five calls sum 5 a draw, yet 62% of those positions are
wins.

| rule of five | 3 | 4 | 5 | 6 | 7+ |
| --- | --- | --- | --- | --- | --- |
| White wins | 9% | 23% | **62%** | 96% | 100% |

### [Does thinking at the right moments make you better?](experiments/thinking)

Not measurably. Players who spend their time on the right moves do not gain more rating the next
year. Players who make fewer errors do.

### [Can statistics catch a chess cheater?](experiments/cheating)

Only a heavy one. Honest players differ so much that a cheater who removes fewer than 0.9 mistakes a
game is flagged less than half the time. And with enough games, most honest players look guilty.

[![Honest players whose best run looks like proof, by games played](experiments/cheating/cheating.svg)](experiments/cheating)

## Run it

```sh
make quick   # redraw the charts, in seconds
make data    # download the data, about 19 GB
make all     # rerun everything, about 8 hours
```

It requires Linux, [uv](https://docs.astral.sh/uv/), make and a C compiler.

## Data

Games from the [Lichess database](https://database.lichess.org), ratings from
[FIDE](https://ratings.fide.com), endgames from the [Syzygy tables](https://tablebase.lichess.ovh)
and analysis by [Stockfish](https://stockfishchess.org).

## License

GPL 3.0 or later. Fathom, in `fathom/`, is MIT.
