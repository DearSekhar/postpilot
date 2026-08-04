"""
Tracks recently generated posts (topic, category, date) so the LLM, which
has no memory between runs, can be told what to avoid repeating, and so
content_mix balancing has real data to work from.
"""
import json
import os
from datetime import date

HISTORY_PATH = os.path.join(os.path.dirname(__file__), "topic_history.json")
MAX_HISTORY = 20


def load_recent_posts() -> list[dict]:
    if not os.path.exists(HISTORY_PATH):
        return []
    with open(HISTORY_PATH, "r") as f:
        data = json.load(f)
    return [d if isinstance(d, dict) else {"topic": d, "category": "unknown", "date": ""} for d in data]


def record_post(topic: str, category: str, industry: str | None = None, problem_id: str | None = None, diagram_style: str | None = None) -> None:
    history = load_recent_posts()
    entry = {"topic": topic, "category": category, "date": date.today().isoformat()}
    if industry:
        entry["industry"] = industry
    if problem_id:
        entry["problem_id"] = problem_id
    if diagram_style:
        entry["diagram_style"] = diagram_style
    history.append(entry)
    history = history[-MAX_HISTORY:]
    with open(HISTORY_PATH, "w") as f:
        json.dump(history, f, indent=2)
