# Where are chess games lost?

Mostly to plain mistakes in the opening and middlegame. But the clock matters more as players get
stronger. Online, it costs 25% of the points lost below 1200, and 38% at 2100–2399. Over the board,
it costs 22% below 1800, and 55% at 2400+.

![The clock's share of the points lost: online and over the board, by rating](decided.svg)

## How it works

1. We take 316,562 online games from Lichess (October 2026) and 427,382 classical over-the-board
   games relayed on Lichess (July 2024 to October 2026). Almost every move has an engine
   evaluation.
2. After every move, we call the position won, drawn or lost. Won means the engine gives a side
   3 pawns or more. With six pieces or fewer, we use the perfect answer of the endgame tables.
3. We find the move that decided the game: the last move after which the position matches the
   final result. If the final position does not match the result, the game was decided off the
   board: a player resigned or lost on time in a position that was not lost, or agreed a draw while
   winning.
4. We charge the lost points to the player who made that move, and sort them by cause: the clock (a
   loss on time, or a deciding mistake with less than 10% of the time left), an endgame mistake, or
   an opening or middlegame mistake.
5. We add it all up per 100 games, by rating.

## What we found

- Stronger players make fewer deciding mistakes, but lose as many points or more to the clock.
- Endgames with six pieces or fewer decide only 1.5% of online games and 1% of over-the-board
  games.
- 11% of online blitz games are decided off the board. In bullet it is 27%, in rapid 7%, and over
  the board 4%.
- A blunder invites another. Right after an opponent's blunder, a player blunders 2.1 times as
  often as usual online, and 3.4 times as often over the board. After their own blunder, if the
  opponent does not blunder back, 1.3 times.
- Gifts often go unpunished. Online below 1200, 39% of blunders are not punished on the next move
  (58% within three moves). At 2400+, 28% (44%). Over the board, 27% below 1800 and 16% at 2400+.
- Some players resign too early: 4% of online blitz resignations come in positions that are not
  lost. In [one game](https://lichess.org/game/wFxi2JL6), a 1912 player resigned a drawn rook
  endgame with two minutes left.

## What to keep in mind

- These are counts, not experiments. They show where points are lost, not how to fix it.
- Online, only games that someone asked Lichess to analyse have evaluations. We reweight them to
  match all games.
- The evaluations stored with the games are quick ones. A deeper check confirmed 126 of 150
  "not lost" resignations.
- Broadcasts miss most games of weaker events.

## Run it

    make data       # once, about 19 GB
    make decided    # about 35 minutes

The code holds the exact definitions.
