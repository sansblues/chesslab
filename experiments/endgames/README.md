# Do textbook endgame rules hold under perfect play?

Mostly, but not at the edges. Endgames with up to seven pieces are solved: tables give the perfect
result of every position. So we checked famous rules against every position they cover.

| rule of five | 3 | 4 | 5 | 6 | 7+ |
| --- | --- | --- | --- | --- | --- |
| White wins | 9% | 23% | **62%** | 96% | 100% |

## How it works

1. We write each rule as a small program. Take the rule of five, for rook and pawn against rook:
   add the pawn's rank and the number of files the defending king is cut off. More than five wins;
   five or less draws.
2. We list every position the rule is meant for. We read each rule generously: quiet positions
   only, with the pieces placed the way the books show.
3. We look up every position in the Syzygy tables and count where the rule is right and where it
   is wrong.

## What we found

- **The rule of five fails at its edge.** At a sum of 5 it says draw, but 62% of those positions
  are wins. Over all 8,990 positions, it is right 86% of the time.
- **One condition makes it exact.** With a sum of 6 or more and the cutting rook below the pawn,
  White wins all 3,493 positions. It still fails with the king cut off on the short side, with
  Black to move, or with a knight pawn.
- **Philidor's defence, followed word for word, loses its own textbook position:** 1...Rb6 2.Rh8+
  Kc7 3.d6+ Kd7??, where only 3...Rxd6 draws. Any player would take the free pawn, but the rule as
  written does not.
- **"Two rook pawns are often a draw" is wrong.** The a- and h-pawn win 97.5% of quiet positions
  with White to move, and still 80% when Black's king blocks one of them.
- **Doubled pawns with the king cut off on the short side are called a draw**, yet 59% are wins
  with White to move.
- **Some rules hold.** Connected pawns win 95% of the time; doubled pawns with the king in front
  only 12%.
- **Pawns with one empty file between them are the hardest to win.** a+c (or f+h) win 78.5%, b+d
  87.4% and c+e 93.1%, each less than both neighbours. In real games, a+c endings are won 45% of the
  time, a+b endings 80%.
- **No short rule is perfect.** A rule of five with 2 branches is right 91.6% of the time. It takes
  75 branches to reach 99%.
- **The best rules are safe ones.** In king and pawn against king, a rule that never wrongly claims
  a win becomes perfect after 21 half-moves of calculation. The textbook rule is still wrong in 98
  positions after 40.

## Try it yourself

The checker tests a rule against every position it covers:

    make -C experiments/endgames slices   # once
    cd experiments/endgames
    uv run python check.py rules/rule_of_five.py

```
White to move: 8,990 positions, White wins 84.1%
  rule_of_five    85.7% right: 84 false wins, 1,199 false draws
  sharpened       3,493 claimed wins, 0 wrong
rule_of_five, false win: 2r5/8/8/8/7k/4R3/2P5/1K6 w - - 0 1
...
```

Two more examples come with it: `rules/two_rook_pawns.py` and `rules/philidor.py`. Copy one to test
your own rule.

## What to keep in mind

- We read each rule our way. A book may mean something narrower.
- We quote the rules from Wikipedia, which cites the books: Soltis, Mednis, Emms, Nunn, and Müller
  and Lamprecht.
- Every legal position counts the same, but real games reach only a few of them.

## Run it

    make data       # once, about 19 GB
    make endgames   # about 50 minutes

The code holds the exact definitions.
