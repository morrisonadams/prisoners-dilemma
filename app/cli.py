import argparse, csv, json, os, datetime, random
from typing import List, Type, Dict, Any
from .engine import Payoffs, play_match
from . import strategies as S

def resolve_strategies(only: List[str], exclude: List[str]):
    all_classes: List[Type] = S.ALL_STRATEGIES
    def canon(x: str) -> str:
        return x.lower().strip().replace("-", "").replace("_", "")
    only_c = set(map(canon, only)) if only else None
    exclude_c = set(map(canon, exclude)) if exclude else set()

    selected = []
    for cls in all_classes:
        name = canon(cls.__name__)
        if only_c is not None and name not in only_c:
            continue
        if name in exclude_c:
            continue
        selected.append(cls)
    return selected

def write_csv(path: str, rows: List[Dict[str, Any]]):
    fieldnames = sorted({k for row in rows for k in row.keys()})
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)

def main():
    parser = argparse.ArgumentParser(description="Iterated Prisoner's Dilemma Tournament")
    parser.add_argument("--rounds", type=int, default=150, help="Rounds if continuation is 0")
    parser.add_argument("--continuation", type=float, default=0.0, help="Continuation probability per round, 0 for fixed rounds")
    parser.add_argument("--noise", type=float, default=0.0, help="Probability that a move is flipped")
    parser.add_argument("--repeats", type=int, default=1, help="Independent tournament repetitions")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--payoffs", type=str, default='{"T":5,"R":3,"P":1,"S":0}', help="JSON for payoffs")
    parser.add_argument("--only", type=str, default="", help="Comma separated strategy names to include")
    parser.add_argument("--exclude", type=str, default="", help="Comma separated strategy names to exclude")
    parser.add_argument("--format", type=str, default="csv", choices=["csv","json"], help="Output format")
    parser.add_argument("--labels", action="store_true", help="List strategy names and exit")
    args = parser.parse_args()

    if args.labels:
        for cls in S.ALL_STRATEGIES:
            print(cls.__name__)
        return

    only_list = [x for x in args.only.split(",") if x.strip()] if args.only else []
    exclude_list = [x for x in args.exclude.split(",") if x.strip()] if args.exclude else []

    pay = json.loads(args.payoffs)
    payoffs = Payoffs(T=int(pay["T"]), R=int(pay["R"]), P=int(pay["P"]), S=int(pay["S"]))

    rng = random.Random(args.seed)

    strategy_classes = resolve_strategies(only_list, exclude_list)
    if len(strategy_classes) < 2:
        raise SystemExit("Need at least two strategies to run a tournament")

    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    out_dir = os.environ.get("OUT_DIR", "/out")
    os.makedirs(out_dir, exist_ok=True)
    tag = f"pd_{timestamp}"
    standings_rows = []
    all_results = []

    for rep in range(args.repeats):
        players = [cls() for cls in strategy_classes]
        names = [p.__class__.__name__ for p in players]

        for i, a in enumerate(players):
            for j, b in enumerate(players):
                if j <= i:
                    continue
                res = play_match(a, b, rounds=args.rounds, continuation=args.continuation, noise=args.noise, payoffs=payoffs, rng=rng)
                row_ab = {
                    "rep": rep,
                    "A": names[i],
                    "B": names[j],
                    "rounds": res["rounds"],
                    "score_A": res["scores"]["A"],
                    "score_B": res["scores"]["B"],
                    "avg_A": round(res["avg"]["A"], 4),
                    "avg_B": round(res["avg"]["B"], 4),
                    "history_A": res["history"]["A"],
                    "history_B": res["history"]["B"],
                }
                all_results.append(row_ab)

    totals: Dict[str, float] = {}
    games: Dict[str, int] = {}
    for row in all_results:
        for side in ["A","B"]:
            name = row[side]
            score = row[f"score_{side}"]
            rounds = row["rounds"]
            totals[name] = totals.get(name, 0.0) + score
            games[name] = games.get(name, 0) + rounds

    standings = [{"strategy": k, "total_score": totals[k], "total_rounds": games[k], "avg_per_round": round(totals[k]/games[k], 4)} for k in totals]
    standings.sort(key=lambda r: (-r["avg_per_round"], -r["total_score"], r["strategy"]))

    if args.format == "csv":
        write_csv(os.path.join(out_dir, f"{tag}_matches.csv"), all_results)
        write_csv(os.path.join(out_dir, f"{tag}_standings.csv"), standings)
        with open(os.path.join(out_dir, f"{tag}_summary.json"), "w", encoding="utf-8") as f:
            json.dump({
                "params": vars(args),
                "strategies": [cls.__name__ for cls in strategy_classes],
                "standings": standings[:5]
            }, f, indent=2)
        print(f"Done. See CSVs and JSON in {out_dir}")
    else:
        with open(os.path.join(out_dir, f"{tag}_results.json"), "w", encoding="utf-8") as f:
            json.dump({
                "params": vars(args),
                "strategies": [cls.__name__ for cls in strategy_classes],
                "matches": all_results,
                "standings": standings
            }, f, indent=2)
        print(f"Done. See JSON in {out_dir}")

if __name__ == "__main__":
    main()
