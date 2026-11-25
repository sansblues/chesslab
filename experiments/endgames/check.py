"""Check an endgame rule against the Syzygy tablebases.

usage: uv run python experiments/endgames/check.py rules/rule_of_five.py

A rule file names its MATERIAL, such as "KRPvKR" (White has the pawns), and holds either
- region(p) with RULES, WIN_CLAIMS or both. p is an endgame.Slice: the positions with
  White's pawns on fixed squares (p.pawns, ints) and the other pieces anywhere (numpy arrays such as
  p.black_king). region says which positions the rules are about. A rule says win (True) or draw
  (False); a win claim says win (True) or nothing (False). Combine arrays with & | ~; a test of the
  pawns alone may return a plain False. The checker counts every legal position of the region up to
  the a-h mirror, so a region must be its own mirror image.
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
    rules, claims = getattr(rule, "RULES", ()), getattr(rule, "WIN_CLAIMS", ())
    counts, examples = defaultdict(float), defaultdict(list)
    for part in endgame.slices(rule.MATERIAL):
        selected = endgame.mask(rule.region, part)
        if selected is None:
            continue
        wins = part.white_wins
        said = {f: np.broadcast_to(f(part), part.shape) for f in [*rules, *claims]}
        for side, to_move in (("White", part.white_to_move), ("Black", ~part.white_to_move)):
            here = selected & to_move
            counts[side] += part.weight * np.count_nonzero(here)
            counts[side, "wins"] += part.weight * np.count_nonzero(here & wins)
            for f, win in said.items():
                other = ("claimed win", win) if f in claims else ("false draw", ~win & wins)
                for kind, found in (("false win", win & ~wins), other):
                    found = found & here
                    counts[side, f, kind] += part.weight * np.count_nonzero(found)
                    shown = examples[f, kind]
                    if kind != "claimed win" and len(shown) < EXAMPLES:
                        shown += [part.board(i) for i in np.flatnonzero(found)[:EXAMPLES - len(shown)]]

    for side in ("White", "Black"):
        if not counts[side]:
            continue
        print(f"{side} to move: {counts[side]:,.0f} positions, White wins {counts[side, 'wins'] / counts[side]:.1%}")
        for f in rules:
            false_wins, false_draws = counts[side, f, "false win"], counts[side, f, "false draw"]
            print(f"  {f.__name__:16}{1 - (false_wins + false_draws) / counts[side]:.1%} right: "
                  f"{false_wins:,.0f} false wins, {false_draws:,.0f} false draws")
        for f in claims:
            print(f"  {f.__name__:16}{counts[side, f, 'claimed win']:,.0f} claimed wins, "
                  f"{counts[side, f, 'false win']:,.0f} wrong")
    for (f, kind), boards in examples.items():
        for board in boards:
            print(f"{f.__name__}, {kind}: {board.fen()}")


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
