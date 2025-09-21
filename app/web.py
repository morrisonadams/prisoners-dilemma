"""Flask application providing a simple web UI for tournaments."""
from __future__ import annotations

import os
from typing import Any, Dict

from flask import Flask, jsonify, render_template, request

from .engine import Payoffs
from .tournament import list_available_strategies, run_tournament


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")

    @app.get("/")
    def index() -> str:
        return render_template("index.html")

    @app.get("/api/strategies")
    def api_strategies():
        return jsonify({"strategies": list_available_strategies()})

    @app.post("/api/run")
    def api_run():
        payload: Dict[str, Any] = request.get_json(silent=True) or {}
        try:
            rounds = int(payload.get("rounds", 150))
            continuation = float(payload.get("continuation", 0.0))
            noise = float(payload.get("noise", 0.0))
            repeats = int(payload.get("repeats", 1))
            seed = payload.get("seed")
            seed = int(seed) if seed not in (None, "") else None

            payoff_data = payload.get("payoffs") or {}
            payoffs = Payoffs(
                T=int(payoff_data.get("T", 5)),
                R=int(payoff_data.get("R", 3)),
                P=int(payoff_data.get("P", 1)),
                S=int(payoff_data.get("S", 0)),
            )

            selected = payload.get("strategies") or None
            exclude = payload.get("exclude") or None

            result = run_tournament(
                rounds=rounds,
                continuation=continuation,
                noise=noise,
                repeats=repeats,
                seed=seed,
                payoffs=payoffs,
                only=selected,
                exclude=exclude,
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:  # pragma: no cover - generic safeguard
            return jsonify({"error": "Failed to run tournament", "details": str(exc)}), 500

        return jsonify(result)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
