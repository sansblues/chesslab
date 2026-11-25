# Does more clock at move 20 go with better results?

Yes, a little. In classical chess, reaching move 20 with 10% more of your time goes with about +8
Elo. For players who are usually short of time by then, it goes with +14: they are the ones who end
up in time trouble. Both numbers already count the small cost of playing faster early.

The less time you have left, the more extra time goes with:

![Elo with 10% more time at move 20: +28 when 10% of the time is left, +5 at 60%](clock.svg)

## How it works

1. We take 695,509 classical over-the-board games, seen from one side at move 20, from 45,833 FIDE
   players (July 2024 to October 2026). Every move has a clock time and an engine evaluation.
2. For each player, we note how much of their time is left at move 20. "Time" is the base time plus
   40 increments: 110 minutes in a 90+30 game.
3. We compare each player with themselves: games where they had more time at move 20 against games
   where they had less, in positions the engine rates the same.
4. That gives the value of extra time later in the game. But saving it costs something: thinking
   less early means a few more early mistakes. We measure that cost from the same players in faster
   and slower time controls, and subtract it.
5. We do the same for online blitz and rapid games from Lichess.

## What we found

| Elo with 10% more time at move 20 | all players | usually short of time |
| --- | --- | --- |
| Classical, over the board | +8 | +14 |
| Online blitz | +17 | +23 |
| Online rapid | +6 | +9 |

- The classical numbers are precise to about ±1.5 Elo. Online they are rougher, and rapid could be
  zero.
- Extra time mostly keeps players out of time trouble. Over the board, it falls from 55% of games
  to 44%. In online blitz, losses on time fall from 12% of games to 7%.
- "Usually short of time" means the fifth of regular players with the least time at move 20. They
  have 32% of their time left there, typical players 48%. They end up in time trouble in 81% of
  their games.
- Late arrivals back it up. Players who lost 10% of their time before move 1 scored about 7 Elo
  less, even though they won back 39% of it by playing faster.
- At 60+30, the same 4,417 players got into time trouble more often than at 90+30 (57% of games
  against 50%), but made no more deciding mistakes. FIDE made 60+30 a standard time control in
  November 2026.

## What to keep in mind

- This compares games; it is not an experiment. A player who keeps more time may simply be in
  better form that day. A second, independent estimate, from how long each game followed the
  player's own opening preparation, came out about a third smaller.
- We added the cost of playing faster early after we saw the first results.
- Games that end before move 20 are left out, and relayed clocks are sometimes wrong.
- It needs a check on new data before it becomes advice.

## Run it

    make data       # once, about 19 GB
    make clock      # about 2.5 hours, most of it engine analysis

The code holds the exact definitions.
