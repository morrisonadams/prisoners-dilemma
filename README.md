# Prisoner's Dilemma Tournament (Dockerized)

Run an Axelrod-style Iterated Prisoner's Dilemma tournament locally with Docker.
Includes classic strategies like TitForTat, GrimTrigger, WinStayLoseShift, and more.

## Quick start

```bash
# 1) Build the image
docker compose build

# 2) Start the web UI (http://127.0.0.1:5000)
docker compose up

# 3) Run a one-off tournament via the CLI
docker compose --profile cli run --rm pd

# 4) Run with options
docker compose --profile cli run --rm pd --rounds 200 --repeats 3 --noise 0.03 --continuation 0.0 --seed 123

# 5) Results
# CSVs and JSON summaries will be written to ./out on your machine
ls out
```

## Web interface

A lightweight Flask UI is included for exploring tournaments interactively.

```bash
# Install the package locally (creates a virtualenv if desired)
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Start the web server
flask --app app.web run

# Visit http://127.0.0.1:5000/ in your browser
```

Alternatively, you can launch the same UI with Docker using `docker compose up`
and browse to [http://127.0.0.1:5000](http://127.0.0.1:5000).

The web UI lets you pick strategies, tweak tournament parameters, and view standings/match breakdowns without leaving the browser.

## Options

- `--rounds`: Fixed number of rounds per match if `--continuation` is 0. Default 150
- `--continuation`: Probability that the game continues after each round. Use 0 for fixed rounds. Default 0.0
- `--noise`: Probability that a move is flipped after a strategy decides. Default 0.0
- `--repeats`: Number of independent tournament repetitions. Default 1
- `--seed`: Random seed for reproducibility
- `--payoffs`: JSON for payoff matrix with keys T,R,P,S. Example `--payoffs '{"T":5,"R":3,"P":1,"S":0}'`
- `--only`: Comma-separated list of strategy names to include
- `--exclude`: Comma-separated list of strategy names to exclude
- `--format`: Output format. csv or json. Default csv
- `--labels`: Print strategy descriptions and exit

## Media layer overview

The tournament engine can simulate a lightweight media network that reports
match outcomes to participating strategies. Each **outlet** advertises:

* `coverage` – probability an outlet reports on a particular match
* `accuracy` – probability the report mirrors the real outcome (otherwise a rumour is broadcast)
* `delay` – number of tournament ticks before the report is delivered (integer or list)

Strategies can optionally subscribe to outlets via enrollment rules that limit
the number of feeds each player follows. The CLI ships with two built-in
presets (`none` and `basic`) and accepts arbitrary JSON describing the network.

### Configuration examples

Example configurations live in `outlets/`. The `balanced.json` preset
demonstrates a mix of highly accurate but slower outlets alongside more
speculative sources:

```json
{
  "outlets": [
    {"name": "GlobalTruth", "coverage": 0.8, "accuracy": 0.97, "delay": [0, 1]},
    {"name": "RegionalObserver", "coverage": 0.65, "accuracy": 0.9, "delay": [1, 2]},
    {"name": "QuickTake", "coverage": 0.45, "accuracy": 0.7, "delay": [0, 1, 2, 3]}
  ],
  "subscriptions": {
    "limit": 2,
    "defaults": {
      "TitForTat": ["GlobalTruth"],
      "WinStayLoseShift": ["GlobalTruth", "RegionalObserver"],
      "Random": ["QuickTake"]
    }
  }
}
```

Run a tournament with that network by piping the JSON to `--media-config`:

```bash
docker compose --profile cli run --rm pd \
  --media-config "$(cat outlets/balanced.json)" \
  --rounds 200 --seed 42
```

For a more sensational environment with high coverage but lower accuracy, try
`outlets/sensational.json`. The CLI help text lists built-in presets and points
to the directory of ready-made samples.

### Strategies that react to media

Strategies inherit from `BaseStrategy`, which provides a `receive_media`
callback invoked whenever an enrolled outlet publishes a story. The default
implementation records reports in the `.rumors` list so strategies can inspect
them from `decide`:

```python
from .base import BaseStrategy

class ReactiveTitForTat(BaseStrategy):
    """Punish if a trusted outlet reports betrayal."""

    def reset(self):
        super().reset()
        self._betrayed = False

    def receive_media(self, report):
        if not report.accurate:
            return
        players = report.payload["players"]
        histories = report.payload["history"]
        opponent = players["A"] if players["B"] == self.name() else players["B"]
        if histories.get(opponent, "").endswith("D"):
            self._betrayed = True

    def decide(self, my_history, opp_history, round_index):
        if self._betrayed:
            return "D"
        return "D" if opp_history and opp_history[-1] == "D" else "C"
```

Use `reset` for per-match cleanup and `media_reset` if you also need to clear
state between tournaments. Always guard against rumours by checking
`report.accurate` or other payload fields that outlets may swap when accuracy
rolls fail.

## Add your own strategy

Create a new file in `app/strategies/` and implement a class deriving from `BaseStrategy`.
The class name becomes the strategy name by default.

Minimal example:

```python
from .base import BaseStrategy

class MyAlwaysC(BaseStrategy):
    def decide(self, my_history, opp_history, round_index):
        return "C"
```

Rebuild the image to include it:

```bash
docker compose build
```

## Structure

- `app/cli.py` CLI entry point
- `app/engine.py` tournament logic
- `app/strategies/` built-in strategies
- `out/` results mounted outside the container

## Developer notes

* The CLI `--seed` option seeds the tournament RNG and is forwarded into the
  `MediaNetwork`, so identical seeds reproduce outlet coverage/accuracy rolls
  and the resulting rumour cascades. When writing your own scripts call
  `run_tournament(..., rng=random.Random(seed))` or pass a seeded `random.Random`
  instance into `MediaNetwork.from_config` to mirror CLI behaviour.
* Outlets draw all randomness from the shared RNG; match continuation checks do
  as well. If you also rely on noisy moves, seed Python's global RNG with the
  same value before running a tournament to mirror CLI runs exactly.

## License

MIT
# prisoners-dilemma
