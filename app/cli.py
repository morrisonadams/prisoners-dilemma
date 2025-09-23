import argparse
import csv
import datetime
import json
import os
from typing import Any, Dict, List, Sequence

from .engine import Payoffs
from .tournament import list_available_strategies, run_tournament
from .media import MEDIA_PRESETS, resolve_media_config

def write_csv(path: str, rows: List[Dict[str, Any]], fieldnames: Sequence[str] | None = None):
    keys = {k for row in rows for k in row.keys()}
    if fieldnames is None:
        field_list = sorted(keys)
    else:
        field_list = list(fieldnames)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=field_list)
        w.writeheader()
        for row in rows:
            w.writerow({name: row.get(name, "") for name in field_list})

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
    parser.add_argument(
        "--media-config",
        type=str,
        default="",
        help=(
            "JSON string or preset name for media network configuration "
            f"(presets: {', '.join(sorted(MEDIA_PRESETS))}; "
            "see outlets/*.json for coverage vs. accuracy examples)"
        ),
    )
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

    media_config = None
    if args.media_config:
        try:
            media_config = resolve_media_config(args.media_config)
        except (ValueError, TypeError) as exc:
            raise SystemExit(str(exc))

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
            media=media_config,
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
    media_data = result.get("media") or {}
    media_reports = media_data.get("reports") if isinstance(media_data, dict) else None
    media_rows: List[Dict[str, Any]] = []
    if isinstance(media_reports, dict):
        for strategy_name, entries in media_reports.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                payload = entry.get("payload") or {}
                payload_json = json.dumps(payload, sort_keys=True)
                match_id = entry.get("match_id")
                match_id_json = json.dumps(match_id) if match_id is not None else ""
                media_rows.append(
                    {
                        "strategy": strategy_name,
                        "outlet": entry.get("outlet", ""),
                        "rep": entry.get("rep", ""),
                        "ordinal": entry.get("ordinal", ""),
                        "match_id": match_id_json,
                        "accurate": entry.get("accurate", ""),
                        "delay": entry.get("delay", ""),
                        "payload": payload_json,
                    }
                )

    if args.format == "csv":
        write_csv(os.path.join(out_dir, f"{tag}_matches.csv"), matches)
        write_csv(os.path.join(out_dir, f"{tag}_standings.csv"), standings)
        if media_data:
            media_csv_path = os.path.join(out_dir, f"{tag}_media_reports.csv")
            media_fields = ["strategy", "outlet", "rep", "ordinal", "match_id", "accurate", "delay", "payload"]
            write_csv(media_csv_path, media_rows, fieldnames=media_fields)
            media_json_path = os.path.join(out_dir, f"{tag}_media_reports.json")
            with open(media_json_path, "w", encoding="utf-8") as f:
                json.dump(media_data, f, indent=2)
        with open(os.path.join(out_dir, f"{tag}_summary.json"), "w", encoding="utf-8") as f:
            json.dump({
                "params": vars(args),
                "strategies": strategies,
                "standings": standings[:5],
                "media": {
                    "config": media_data.get("config") if isinstance(media_data, dict) else None,
                    "reports": {name: len(entries) for name, entries in (media_reports or {}).items()},
                },
            }, f, indent=2)
        print(f"Done. See CSVs and JSON in {out_dir}")
    else:
        with open(os.path.join(out_dir, f"{tag}_results.json"), "w", encoding="utf-8") as f:
            json.dump({
                "params": vars(args),
                "strategies": strategies,
                "matches": matches,
                "standings": standings,
                "media": media_data,
            }, f, indent=2)
        print(f"Done. See JSON in {out_dir}")

if __name__ == "__main__":
    main()
