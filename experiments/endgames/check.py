"""Check an endgame rule against the Syzygy tablebases.

usage: uv run python experiments/endgames/check.py rules/rule_of_five.py

A rule file names its MATERIAL, such as "KRPvKR" (White has the pawns), and holds either
- region(p) and RULES. p is an endgame.Slice: the positions with White's pawns on fixed squares
  (p.pawns, ints) and the other pieces anywhere (numpy arrays such as p.black_king). region says
  which positions the rules are about, each rule whether White wins. Combine arrays with & | ~;
  a test of the pawns alone may return a plain False. The checker counts every legal position of
  the region up to the a-h mirror, so a region must be its own mirror image.
- START and policy(board), Black's move. The checker plays the policy against every White move
  from START. It stops at the first policy move that turns the tablebase draw into a loss, or,
  if there is none, proves that the policy holds the draw."""
import sys
from collections import defaultdict
from pathlib import Path

import chess
import endgame
import numpy as np

from chesslab import tablebase

EXAMPLES = 2


def check_rules(rule):
    counts, examples = defaultdict(float), defaultdict(list)
    for part in endgame.slices(rule.MATERIAL):
        selected = endgame.mask(rule.region, part)
        if selected is None:
            continue
        wins = part.white_wins
        said = {f: np.broadcast_to(f(part), part.shape) for f in rule.RULES}
        for side, to_move in (("White", part.white_to_move), ("Black", ~part.white_to_move)):
            here = selected & to_move
            counts[side, "positions"] += part.weight * np.count_nonzero(here)
            counts[side, "wins"] += part.weight * np.count_nonzero(here & wins)
            for f in rule.RULES:
                for kind, wrong in (("false wins", said[f] & ~wins), ("false draws", ~said[f] & wins)):
                    wrong &= here
                    counts[side, f.__name__, kind] += part.weight * np.count_nonzero(wrong)
                    found = examples[f.__name__, kind]
                    if len(found) < EXAMPLES:
                        found += [part.board(i) for i in np.flatnonzero(wrong)[:EXAMPLES - len(found)]]

    print(f"{'side to move':12}  {'positions':>13}  {'White wins':>10}  {'rule':16}  {'accuracy':>8}  "
          f"{'false wins':>12}  {'false draws':>12}")
    for side in ("White", "Black"):
        positions = counts[side, "positions"]
        if not positions:
            continue
        for f in rule.RULES:
            false_wins, false_draws = counts[side, f.__name__, "false wins"], counts[side, f.__name__, "false draws"]
            print(f"{side:12}  {positions:13,.0f}  {counts[side, 'wins'] / positions:10.1%}  {f.__name__:16}  "
                  f"{1 - (false_wins + false_draws) / positions:8.1%}  {false_wins:12,.0f}  {false_draws:12,.0f}")
    for (name, kind), boards in examples.items():
        for board in boards:
            print(f"{name}, {kind[:-1]}: {board.fen()}")


def check_policy(rule):
    start = chess.Board(rule.START)
    if tablebase.wdl(start) != 0:
        sys.exit(f"{rule.START} is not a draw")
    parents = {start.epd(): None}  # position -> (previous position, Black's move, White's move)
    frontier = [start]
    while frontier:
        following = []
        for board in frontier:
            if board.is_stalemate():
                continue
            node, move = board.epd(), rule.policy(board)
            if move not in board.legal_moves:
                return report(rule, parents, board, None)
            capture = board.is_capture(move)
            board.push(move)
            if tablebase.wdl(board) == 1:
                board.pop()
                return report(rule, parents, board, move)
            for reply in [] if capture else board.legal_moves:
                if not board.is_capture(reply) and not reply.promotion:  # else the game leaves the material
                    board.push(reply)
                    if board.epd() not in parents:
                        parents[board.epd()] = node, move, reply
                        following.append(board.copy(stack=False))
                    board.pop()
        frontier = following
    print(f"The policy holds the draw: {len(parents):,} positions with Black to move.")


def report(rule, parents, board, move):
    """The line from START to the losing move, and the moves that draw instead."""
    moves, key = [], board.epd()
    while parents[key]:
        key, black, white = parents[key]
        moves[:0] = [black, white]
    line = chess.Board(rule.START).variation_san(moves + [move] if move else moves)
    drawing = []
    for m in board.legal_moves:
        board.push(m)
        drawing += [m] if tablebase.wdl(board) != 1 else []
        board.pop()
    print(f"The policy loses: {line}{'??' if move else ' (no legal move)'}")
    print(f"Drawing moves: {', '.join(board.san(m) for m in drawing) or 'none'}. "
          f"Positions with Black to move: {len(parents):,}.")


if __name__ == "__main__":
    path = Path(sys.argv[1])
    rule = endgame.load(path if path.exists() else Path(__file__).parent / path)
    print(f"{path}: {rule.MATERIAL}")
    check_policy(rule) if hasattr(rule, "policy") else check_rules(rule)
