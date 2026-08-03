"""
Agentic workflow execution trace experiment (stretch feature).

Runs the integrated ``RecommendationAgent`` on the High-Energy Pop profile and
saves the observable execution trace as JSON. It uses the trace the agent
already attaches — it does not duplicate any agent logic.

Reproducible and non-interactive:

    python3 -m experiments.generate_agent_trace
"""

import json

from src.recommender import load_songs
from src.agent import RecommendationAgent

TRACE_PATH = "experiments/agent_trace_example.json"

PROFILE = {
    "favorite_genre": "pop",
    "favorite_mood": "happy",
    "target_energy": 0.85,
    "likes_acoustic": False,
}


def main() -> None:
    songs = load_songs("data/songs.csv")
    agent = RecommendationAgent(songs)

    result = agent.recommend(PROFILE, k=5, mode="balanced")
    trace_data = result.trace.to_dict()

    with open(TRACE_PATH, "w", encoding="utf-8") as handle:
        json.dump(trace_data, handle, indent=2)
        handle.write("\n")

    print(f"Trace written to {TRACE_PATH}")
    print(
        f"request_id={trace_data['request_id']} | "
        f"final_status={trace_data['final_status']} | "
        f"steps={len(trace_data['steps'])}"
    )
    for step in trace_data["steps"]:
        print(f"  {step['step']}. {step['component']}: {step['status']}")


if __name__ == "__main__":
    main()
