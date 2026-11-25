# Does thinking at the right moments make you better?

Not measurably. Players who spend their time where it matters most do not gain more rating in the
next year: +0.18 Elo per SD of allocation quality (95% CI −1.84 to +2.21, 3,973 players). But the
measure is mostly noise, so the test only excludes true effects larger than about 8 to 14 Elo a
year.

![Time allocation does not predict rating change; errors do](thinking.svg)

## Findings

- The analysis plan was written before any outcome was computed ([PLAN.md](PLAN.md)). The
  positive control works: the error in a player's games predicts rating change
  (−12.1 Elo per SD, p < 1e−10).
- Split-half reliability of allocation quality (3 games against 3): 0.041 (95% CI 0.013 to
  0.073), against 0.45 for the mean think time and 0.53 for its variability. A reliability of 0.7 would need about 162 games a player.
- On average, stronger players do allocate better: the correlation of think time with the value
  of thinking rises from 0.115 (rating ≤ 1600) to 0.165 (> 2400), as Russek et al. (Cognitive
  Science, 2025) found.
- Within a player, games with better allocation score better: +0.013 points per SD
  (95% CI 0.007 to 0.019, 17,164 games). This is an association only.
- A low clock goes with more error, most of all where the value of thinking is high: with less
  than 10 min left, the error is 0.46 win-% points higher, and 0.99 points more (95% CI 0.86 to
  1.12) in critical positions (top 20%), about 3 times as much. But critical moves played fast
  (< 30 s) hold only 4.8% of all error, and they lose less than critical moves played slowly
  (2.87 against 3.52 win-% points).

## Reproduce

    make data            # once, from the repo root
    make thinking        # about 3 h, one heavy job (Stockfish takes 2.5 h on 12 cores)
    make -C experiments/thinking quick   # the chart from results/, seconds

`engine.py` skips positions already in `data/thinking/stockfish/`, so a stopped run resumes.

## Method

- Data: classical over-the-board games relayed on Lichess in the baseline year (Jul 2024 to
  Jun 2025), with clocks to the second and engine evals on at least 90% of the plies; FIDE standard
  lists of Jul 2024, Jul 2025 and Jul 2026.
- Players: 8,224 with a FIDE ID, at least 10 such games and a rating in the Jul 2025 and Jul 2026
  lists. Analysed: 4,000 of them at random, up to 6 random games each: 635,837 positions, 501,336 of them
  not decided (|eval| ≤ 300 cp). These two cuts, made for compute, were logged before any outcome.
- Positions: the player's moves 9 to 40 with more than one legal move. Think time = clock before −
  clock after + increment.
- Value of thinking (VOC): the win probability of the best move minus that of the move a depth-4
  search prefers, both scored by a 30,000-node search (Stockfish 19); a depth-4 move outside that
  search's top two is scored by a 7,500-node search restricted to the shallow moves. Win
  probability: the Lichess formula, eval clipped to ±1000 cp.
- Allocation quality (AQ): the Spearman correlation of VOC with log(1 + think time), taken relative
  to the player's mean in that game, over the player's positions.
- Model: OLS with HC3 errors. Rating change (Jul 2025 to Jul 2026) on AQ, with rating, rating²,
  age (linear spline), K-factor, sex, error (mean win-probability loss), score above expectation,
  number of games, mean think time, time-trouble rate and the rating change of the year before.
  Permutation null (think times shuffled within each game, 200 times): p = 0.875.
- Reliability: AQ from odd against even games (3 against 3), bootstrap CI. The bound is the upper
  CI limit divided by the square root of the Spearman-Brown reliability.

## Limits

- VOC is a noisy proxy: the depth-4 and depth-8 versions agree only weakly (Spearman 0.336).
- Only 6 games a player were analysed; true effects up to about 8 Elo per SD a year (14 at the
  low end of the reliability CI) remain possible.
- A game that goes well can change how a player uses time: the within-game link need not be causal.
- Fast moves in critical positions can be prepared opening lines, not careless play.
- Broadcasts over-represent strong events, and relayed clocks are sometimes wrong.
