import argparse
import csv
import datetime
import json
import os
from typing import Any, Dict, List

from .engine import Payoffs
from .tournament import list_available_strategies, run_tournament

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
        for info in list_available_strategies():
            print(info["name"])
        return

    only_list = [x for x in args.only.split(",") if x.strip()] if args.only else []
    exclude_list = [x for x in args.exclude.split(",") if x.strip()] if args.exclude else []

    pay = json.loads(args.payoffs)
    payoffs = Payoffs(T=int(pay["T"]), R=int(pay["R"]), P=int(pay["P"]), S=int(pay["S"]))

    try:
        result = run_tournament(
            rounds=args.rounds,
            continuation=args.continuation,
            noise=args.noise,
            repeats=args.repeats,
            seed=args.seed,
            payoffs=payoffs,
            only=only_list,
            exclude=exclude_list,
        )
    except ValueError as exc:
        raise SystemExit(str(exc))

    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    out_dir = os.environ.get("OUT_DIR", "/out")
    os.makedirs(out_dir, exist_ok=True)
    tag = f"pd_{timestamp}"
    matches = result["matches"]
    standings = result["standings"]
    strategies = result["strategies"]

    if args.format == "csv":
        write_csv(os.path.join(out_dir, f"{tag}_matches.csv"), matches)
        write_csv(os.path.join(out_dir, f"{tag}_standings.csv"), standings)
        with open(os.path.join(out_dir, f"{tag}_summary.json"), "w", encoding="utf-8") as f:
            json.dump({
                "params": vars(args),
                "strategies": strategies,
                "standings": standings[:5]
            }, f, indent=2)
        print(f"Done. See CSVs and JSON in {out_dir}")
    else:
        with open(os.path.join(out_dir, f"{tag}_results.json"), "w", encoding="utf-8") as f:
            json.dump({
                "params": vars(args),
                "strategies": strategies,
                "matches": matches,
                "standings": standings
            }, f, indent=2)
        print(f"Done. See JSON in {out_dir}")

if __name__ == "__main__":
    main()
