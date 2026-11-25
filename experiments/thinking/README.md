# Does thinking at the right moments make you better?

Not measurably. Over a year, players who spend their time on the right moves gain no more rating
than others.

## How it works

1. We take 4,000 FIDE-rated players from classical over-the-board games relayed on Lichess between
   July 2024 and June 2025, with up to 6 games each.
2. For each of their moves, an engine measures how much thinking was worth there: how much better
   the best move is than the move a quick look finds.
3. We compare that with how long the player thought. A player who thinks long when it matters, and
   moves fast when it does not, gets a high score.
4. We check whether players with a high score gained more FIDE rating over the next year (July 2025
   to July 2026) than others of the same rating, age and accuracy.

We wrote this plan down before we computed any result: [PLAN.md](PLAN.md).

## What we found

- No link: +0.2 Elo a year per standard deviation of the score, with a 95% range of −1.8 to +2.2.
  The test itself works: players with fewer errors did gain rating, about 12 Elo a year per
  standard deviation.
- The score is mostly noise. A player's score in three games hardly predicts it in three other
  games (correlation 0.04). A reliable score would need about 160 games per player. So the test can
  only rule out effects bigger than about 8 to 14 Elo a year.
- Stronger players do spend their time a bit better on average, as
  [Russek et al. (2025)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12553403) found.
- Within a player, games where they spent their time well went a little better. But a good game may
  also change how a player uses their time.
- Playing a critical move too fast is rarely the problem. Such moves hold only 5% of all lost value,
  and they are slightly better than slow critical moves. Most mistakes in critical positions come
  after thinking.
- Low on time, mistakes grow about three times more in critical positions than in quiet ones.

## What to keep in mind

- The engine's measure of "worth thinking" is rough: two versions of it agree only weakly.
- Only 6 games per player were analysed.
- A fast move in a critical position may be a prepared opening move.
- Broadcasts favour strong events, and relayed clocks are sometimes wrong.

## Run it

    make data       # once, about 19 GB
    make thinking   # about 3 hours, most of it engine analysis

The code holds the exact definitions.
