"""The rule of five (rules/rule_of_five.py) against the KRPvKR tablebase. Writes
results/rule_of_five_by_sum.csv   region R5: positions and White wins by the rule's sum
results/rule_of_five_rules.csv    both rules on R5 and on R5 with one condition changed
results/rule_of_five_tree.csv     the shortest exact rule: decision trees on R6, by depth"""
from pathlib import Path

import endgame
import numpy as np
import pandas as pd
from endgame import file, rank

HERE = Path(__file__).parent
rule = endgame.load(HERE / "rules" / "rule_of_five.py")


def counts(data, mask, said):
    wins = data.white_wins
    return {"positions": int(mask.sum()), "white_wins": int((mask & wins).sum()),
            "predicted_wins": int((mask & said).sum()), "false_wins": int((mask & said & ~wins).sum()),
            "false_draws": int((mask & ~said & wins).sum())}


def gini(y):
    return len(y) * (1 - (y.mean() ** 2 + (1 - y.mean()) ** 2))


def tree(features, wins, depth):
    """Leaves and errors of a decision tree of the given depth that splits by the Gini index."""
    leaves = []

    def grow(index, depth):
        y = wins[index]
        errors = min(y.sum(), len(y) - y.sum())
        best = None
        for x in features.values() if depth and errors else ():
            for value in np.unique(x[index])[:-1]:
                low = x[index] <= value
                impurity = gini(y[low]) + gini(y[~low])
                if best is None or impurity < best[0]:
                    best = impurity, low
        if best is None or best[0] >= gini(y) - 1e-9:
            leaves.append(errors)
        else:
            grow(index[best[1]], depth - 1)
            grow(index[~best[1]], depth - 1)

    grow(np.arange(len(wins)), depth)
    return len(leaves), sum(leaves)


def main():
    data = endgame.table("KRPvKR", rule.cut_off, r5=rule.region)
    pawn_file, pawn_rank, long_side = file(data.pawn), rank(data.pawn), rule.long_side(data)
    r5 = data.r5
    by_sum = data[r5].groupby(rule.total(data[r5]).rename("sum")).white_wins.agg(positions="size", white_wins="sum")
    by_sum.to_csv(HERE / "results" / "rule_of_five_by_sum.csv")

    c_to_f = pawn_file.between(3, 6)
    regions = {"R5": r5, "R5, king on the short side": c_to_f & ~long_side & data.white_to_move,
               "R5, Black to move": c_to_f & long_side & ~data.white_to_move,
               "R5, knight pawn": pawn_file.isin([2, 7]) & long_side & data.white_to_move}
    rows = [{"region": name, "rule": f.__name__} | counts(data, mask, f(data))
            for name, mask in regions.items() for f in rule.RULES]
    pd.DataFrame(rows).to_csv(HERE / "results" / "rule_of_five_rules.csv", index=False)

    r6 = data[r5 & (rank(data.white_rook) <= pawn_rank)]  # the cutting rook not ahead of the pawn
    pawn, side = r6.pawn, np.sign(file(r6.black_king) - file(r6.pawn))
    features = {name: np.asarray(x) for name, x in {
        "sum": rule.total(r6), "pawn rank": rank(pawn), "files cut off": rule.files_cut_off(r6),
        "bishop pawn": file(pawn).isin([3, 6]), "black king rank - pawn rank": rank(r6.black_king) - rank(pawn),
        "black king files beyond rook": abs(file(r6.black_king) - file(r6.white_rook)),
        "white king rank - pawn rank": rank(r6.white_king) - rank(pawn),
        "white king on the black king's side": np.sign(file(r6.white_king) - file(pawn)) == side,
        "white rook rank - pawn rank": rank(r6.white_rook) - rank(pawn),
        "white rook files from pawn": abs(file(r6.white_rook) - file(pawn))}.items()}
    wins, curve = r6.white_wins.to_numpy(), []
    for depth in range(1, 13):
        leaves, errors = tree(features, wins, depth)
        curve.append({"depth": depth, "leaves": leaves, "positions": len(wins), "errors": errors})
        if not errors:
            break
    pd.DataFrame(curve).to_csv(HERE / "results" / "rule_of_five_tree.csv", index=False)
    print(by_sum.to_string(), pd.DataFrame(rows).to_string(index=False), pd.DataFrame(curve).to_string(index=False),
          sep="\n\n")


if __name__ == "__main__":
    main()
