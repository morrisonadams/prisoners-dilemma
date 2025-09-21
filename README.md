# Prisoner's Dilemma Tournament (Dockerized)

Run an Axelrod-style Iterated Prisoner's Dilemma tournament locally with Docker.
Includes classic strategies like TitForTat, GrimTrigger, WinStayLoseShift, and more.

## Quick start

```bash
# 1) Build the image
docker compose build

# 2) Run a default tournament
docker compose run --rm pd

# 3) Run with options
docker compose run --rm pd --rounds 200 --repeats 3 --noise 0.03 --continuation 0.0 --seed 123

# 4) Results
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

## License

MIT
# prisoners-dilemma
