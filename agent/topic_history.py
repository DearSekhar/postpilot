"""
Tracks recently generated topics in a small JSON file so the LLM (which has
no memory between runs) can be explicitly told what to avoid repeating.
"""
import json
import os

HISTORY_PATH = os.path.join(os.path.dirname(__file__), "topic_history.json")
MAX_HISTORY = 15


def load_recent_topics() -> list[str]:
    if not os.path.exists(HISTORY_PATH):
        return []
    with open(HISTORY_PATH, "r") as f:
        return json.load(f)


def record_topic(topic: str) -> None:
    history = load_recent_topics()
    history.append(topic)
    history = history[-MAX_HISTORY:]
    with open(HISTORY_PATH, "w") as f:
        json.dump(history, f, indent=2)
