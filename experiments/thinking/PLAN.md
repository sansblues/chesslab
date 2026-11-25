# Analysis plan

Written on 2026-11-24, before any outcome (future FIDE rating change, game result) was computed.
Only data coverage (clocks, evals, FIDE IDs) had been looked at.

## Question

Does a player's time-allocation quality (how well the time spent per move tracks how much thinking
the position deserves) predict their future FIDE rating change, beyond current rating, age,
accuracy and recent over-performance? Secondary: within a player, are the games with better
allocation the better games?

## Data and windows

- Lichess broadcasts, over-the-board relays with clocks, evals and FIDE IDs. Classical (time control
  from the clocks), not online or engine events, each game once, with a result, at least 90% of
  plies with a clock and with an eval, clocks to the second.
- Baseline (exposure and controls): games of Jul 2024 to Jun 2025.
- Outcome: rating in the Jul 2026 list minus rating in the Jul 2025 list. Prior trend: Jul 2025
  minus Jul 2024.
- Players: a FIDE ID, at least 10 qualifying baseline games, rated in the Jul 2025 and Jul 2026
  lists. Up to 10 baseline games a player (random, seed 7) are analysed with the engine.

## Positions, value of thinking, exposure

- The player's moves 9 to 40. Think time = clock before − clock after + increment (increment from
  the clocks). Dropped: missing clocks, a clock gain above increment + 120 s (time added), think
  times below −2 s or above 3600 s, a single legal move, |deep eval| > 300 cp or mate.
- VOC: win probability of the deep best move minus that of the move a depth-4 search prefers, both
  scored by the deep search (Stockfish 19, 1 thread, fixed nodes; Lichess formula).
- Allocation quality (AQ): Spearman correlation, over the player's positions, of VOC with
  log(1 + think time) demeaned within each game.

## Primary model

OLS with HC3 errors: rating change on z(AQ), rating, rating², age (linear spline, knots 14, 18, 25,
40, 60), K-factor, sex, z(error: mean win-probability loss), z(score above the Elo expectation),
log(games), z(mean log think time), z(time-trouble rate: < 5 min before move 40), and the prior
trend (0 and an indicator if missing). Supported if β(AQ) > 0 with p < 0.05. Also: split-half
reliability of AQ (odd against even games, Spearman-Brown).

## Secondary, pre-specified

Permutation null (time shuffled, 200 times); within-player game level (score above expectation on
game AQ, games with at least 15 positions; associational only); time against VOC by rating (a
replication of earlier work). Also planned, not in this repository: the Nov 2026 outcome, adults
and juniors apart, the rating-only model, two other exposures (best-versus-second-best gap,
critical moves played fast) and a phase-level placebo; all were null in the original run.

## Deviations logged before outcomes were computed (2026-11-24)

- Compute: 4,000 random eligible players (of 8,224), 6 baseline games each; deep search at 30,000
  nodes. Error, over-performance, time trouble and mean time still use all baseline games.

## Not as planned

- The permutation null shuffles think times within each game (the plan says within each player),
  as the original analysis did: AQ is demeaned within each game, so this keeps each game's pace.
