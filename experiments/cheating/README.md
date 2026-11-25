# Can statistics catch a chess cheater?

Only a heavy one. Honest players of the same rating differ by 0.24 mistakes per game. So a cheater
who removes fewer than about 0.9 mistakes per game is flagged less than half the time by a test
that wrongly flags 1 honest player in 10,000, however many games they play.

![Search 10,000 games and 59% of honest players have a 5-game run that looks like 1-in-10,000 evidence](cheating.svg)

## Findings

How many games a test needs to catch 9 cheaters in 10, at the same false-positive rate (all
cheaters are simulated):

- A cheater who fixes the worst move of each game: no number of games is enough.
- One who fixes the 2 worst moves: 97 to 1,017 games below 2200, never from 2200.
- One who fixes the 3 worst moves: 36 to 251 games below 2400, never from 2400.
- One who asks the engine at 1 to 3 random critical moments of an over-the-board game: 123 to
  6,219 games, even if honest players did not differ.

The chart shows the reverse trap. Take an honest player's best 5-game run and test it as if it had
been chosen in advance: it looks like proof. With 10,000 games, 59% of honest players have such a
run.

## Reproduce

    make data            # once, from the repo root
    make cheating        # about 6 min, one heavy job
    make -C experiments/cheating quick   # the chart from results/, seconds

## Method

- Data: the Lichess broadcast of Sep 2026, all events, both ratings 1000-2900, at least 30 plies,
  at most 2 plies without an eval: 20,754 games, 40,960 player-games, 30,230 of them classical
  (first clock at least 50 min) (`sample.csv`).
- A move from ply 16 on loses the drop in the mover's win%, from the Lichess eval in the PGN and the
  Lichess formula (eval clipped to ±10 pawns). Moves in decided positions (win% ≤ 3 or ≥ 97) do not
  count. A mistake loses at least 10 win%. A player-game needs 10 moves with an eval from ply 16 on.
- Honest baseline: mistakes per classical game, by 200-point rating band (`honest_mistakes.csv`):
  2.83 at 1400, 2.27 at 1800, 1.51 at 2200, 0.80 at 2600.
- Spread: mistakes per game are adjusted for rating, rating squared, the rating gap to the opponent
  and the number of counted moves. The between-player SD comes from the method of moments over the
  2,501 players (FIDE ID, else name) with at least 6 classical games, 8.2 games each on average;
  95% CI from 300 bootstrap samples of players: 0.239 (0.180-0.284) (`spread.csv`).
- Test: a player's mean mistakes per game against the honest mean at their rating, one-sided, at a
  false-positive rate of 1e-4 and 90% power. Its null variance is σ_w²/N + σ_b², so with many games
  the threshold tends to 3.72 × σ_b = 0.89 mistakes per game.
- Model A (online): the cheater sees the engine on every move and overrides their k worst moves of
  each game, so m mistakes become max(m − k, 0) (`model_a.csv`).
- Model B (over the board): Stockfish 19 (30,000 nodes, the 2 best moves, Hash 64) judges every
  position from ply 16 of 420 classical games, 60 per 200-point band of average rating 1400-2799,
  rating gap ≤ 300. A critical moment: the best move keeps 10-90 win% and is at least 10 win%
  better than the second best. The cheater asks the engine at k random critical moments of a game;
  the statistic is critical moments missed per game (`model_b.csv`).
- Cherry-picking: per-game loss per move drawn from the 13,224 classical player-games at 2000-2399.
  For 1,000 simulated honest players per number of games, the best 5-game run gets a naive p-value
  against 4 million 5-game runs chosen in advance (`cherry_picking.csv`). The median naive p is
  about 1 / games: 9.1e-4 at 1,000 games, 7.9e-5 at 10,000.
- Related work: Regan's model of move choice, used by FIDE; Turk & Polson 2026, signatures of play
  and an anytime-valid sequential test (arXiv 2606.18544); "ChessFraud: Exploring the Capabilities of
  Human-Aligned Models for Cheating Detection in Online Chess" (doi 10.1145/3770855.3817587); Keren 2026,
  the selective cheater of model A (arXiv 2601.05386).

## Limits

- The model is simple and the cheaters are simulated: one statistic (mistakes per game) and two
  fixed cheating rules; real detectors use more signals and real cheaters other rules.
- The spread comes from about 8 games per player, and part of it may be rating noise (a rating lags
  a player's form).
- The cheater of model A knows their worst moves; a real one fixes fewer mistakes per consultation,
  so they are harder to catch.
- Model B rests on 107 to 134 player-games per band: its numbers are rough.
- Platforms have more data than moves: clock use, behaviour and many more games per player.
