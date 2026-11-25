# Where are chess games lost?

Mostly by plain mistakes in the opening and middlegame. But the clock's share of the points lost
grows with rating: online from 25% below 1200 to 38% at 2100–2399, and over the board from 22%
below 1800 to 55% at 2400+.

![The clock's share of the points lost: online and over the board, by rating](decided.svg)

## Findings

- Stronger players lose fewer points to mistakes, but about as many or more to the clock.
- Endgames with six pieces or fewer decide 1.5% of online games and 1.0% of over-the-board
  classical games.
- In 11.4% of online blitz games the result does not follow from the final position: a player
  resigns or loses on time in a position that is not lost, or the game is drawn in a won position
  (bullet 27.4%, rapid 6.5%, over-the-board classical 4.1%).
- After an opponent's blunder, the reply is itself a blunder 2.13× as often as usual in online
  blitz and 3.38× in over-the-board classical. After a player's own blunder, if the opponent's
  reply is not one, their next move is a blunder 1.32× as often (online blitz).
- An opponent's blunder goes unpunished on the next move 39% of the time in online blitz below
  1200 and 28% at 2400+ (within three moves: 58% and 44%); over the board, 27% below 1800 and 16%
  at 2400+.
- Online, 4.0% of blitz resignations come in positions that are not lost by the recorded eval. A
  deeper search agrees for 126 of 150 such resignations (all speeds). In
  [wFxi2JL6](https://lichess.org/game/wFxi2JL6) a 1912 player resigned a rook endgame that is a
  tablebase draw, with 128 s left.

## Reproduce

    make data            # once, from the repo root
    make decided         # about 35 min, one heavy job
    make -C experiments/decided quick   # the chart from results/, seconds

## Method

- Data: the 316,562 games of the Lichess sample (Oct 2026) with an eval on at least 95% of
  plies, and the 427,382 over-the-board classical broadcast games with evals (Jul 2024 – Oct 2026).
- Each position is won, drawn or lost for White: eval ≥ +3 or ≤ −3 pawns, or the Syzygy value
  at six pieces or fewer. A missing eval keeps the previous class.
- The deciding moment is the last move after which the class equals the result and stays so.
  If the final position's class is not the result, the game was decided off the board
  (resignation, loss on time, draw). The side whose result is below the position's value loses
  the difference, in half-points.
- Causes: clock = a loss on time in a position not lost, or a deciding mistake with less than 10%
  of base + 40 × increment left; endgame = six pieces or fewer, or at most 26 pawns of non-pawn
  material on the board.
- Online figures over all speeds are post-stratified to the whole Lichess sample (cells: speed ×
  average rating band × how the game ended × length); figures by speed are shares of the sample.
- Blunder: the mover's winning chances (Lichess formula, −1..1, eval clipped to ±10 pawns) fall
  by 0.3 or more. Ratios are observed / expected blunders, the expectation from all moves of the
  same population, rating band, winning-chance bin, clock bin and phase.
- Not punished: the reply gives back more than half of what the blunder gained (within 3 moves:
  at any of the next three own moves).
- Re-check: 150 of the non-lost online resignations (all speeds, not in the tablebases; first by MD5
  of the game URL), Stockfish 19 at 3 M nodes.

## Limits

- Lichess has evals only for games that someone asked it to analyse. Weighting corrects only for
  the cell variables.
- The recorded eval of a final position is shallow: the re-check keeps 126 of 150 non-lost
  resignations.
- Broadcast games miss most games of weaker events, and some relays lack clocks.
- A player's rating band comes from their rating in the game header (Lichess or FIDE).
