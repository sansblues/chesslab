# Can statistics catch a chess cheater?

Only a heavy one. Honest players of the same rating differ so much that a cheater who uses the
engine once a game is caught less than half the time, however many games they play. And everyone
has hot streaks: with enough games, most honest players have one that looks like proof of cheating.

![Honest players whose best 5-game streak looks like proof: 9% at 1,000 games, 59% at 10,000](cheating.svg)

## How it works

1. We take 20,754 over-the-board games relayed on Lichess in September 2026, and count each
   player's mistakes: moves that throw away 10% or more of their winning chances.
2. We measure how much honest players of the same rating differ: about 0.24 mistakes per game.
3. We simulate cheaters who let the engine fix some of their moves. Then we ask how many games a
   test needs to catch 9 in 10 of them, while it wrongly flags only 1 honest player in 10,000.
4. We simulate honest players with many games, pick each one's best 5-game streak, and test it as
   if it had been chosen in advance.

## What we found

- To stand out, a cheater must avoid about 0.9 mistakes per game, because honest players already
  differ that much.
- A cheater who fixes their worst move in each game never gets there: no number of games is enough.
- Fixing the 2 worst moves: 97 to 1,017 games below 2200, and never from 2200 up.
- Fixing the 3 worst moves: 36 to 251 games below 2400, and never from 2400 up.
- Asking the engine at 1 to 3 random critical moments over the board: 123 to 6,219 games.
- Hot streaks fool the test. The best 5-game streak looks like 1-in-10,000 proof for 9% of honest
  players with 1,000 games, and 59% with 10,000. The more games, the more streaks to pick from, and
  the best of thousands is extreme by chance alone.

## What to keep in mind

- The model is simple. It looks at one number, mistakes per game. Real detectors also use move
  times, behaviour and many more games.
- The cheaters are simulated, and our worst-move cheater knows exactly which moves are worst. Real
  cheaters are less precise, which makes them even harder to catch.
- The spread between honest players comes from about 8 games each.
- Related work: Regan's model, used by FIDE; [Turk & Polson (2026)](https://arxiv.org/abs/2606.18544);
  [ChessFraud (KDD 2026)](https://doi.org/10.1145/3770855.3817587);
  [Keren (2026)](https://arxiv.org/abs/2601.05386).

## Run it

    make data       # once, about 19 GB
    make cheating   # about 6 minutes

The code holds the exact definitions.
