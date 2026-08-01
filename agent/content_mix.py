"""
Suggests which content category (and, separately, which industry vertical)
to steer toward next, based on declared target mixes (content_mix /
industry_mix) vs what's actually been posted recently. This is a hint fed
into the prompt, not a hard rule — the model still makes the final call,
this just improves the odds of actually hitting the target mix over time
instead of drifting.

Also handles picking a specific business problem for the chosen industry
from industry_problems.json, avoiding ones used recently.
"""
import random
from collections import Counter


def suggest_weighted(mix: dict, recent_posts: list, field: str, window: int = 10) -> str | None:
    """Generic version: balances any field (e.g. 'category' or 'industry')
    against its target mix percentages."""
    if not mix:
        return None

    recent = recent_posts[-window:]
    if not recent:
        return max(mix, key=mix.get)

    counts = Counter(p.get(field) for p in recent if p.get(field) in mix)
    total = len(recent)

    deficits = {}
    for key, target_pct in mix.items():
        actual_pct = (counts.get(key, 0) / total) * 100
        deficits[key] = target_pct - actual_pct

    return max(deficits, key=deficits.get)


def suggest_category(content_mix: dict, recent_posts: list, window: int = 10) -> str | None:
    return suggest_weighted(content_mix, recent_posts, field="category", window=window)


def suggest_industry(industry_mix: dict, recent_posts: list, window: int = 10) -> str | None:
    return suggest_weighted(industry_mix, recent_posts, field="industry", window=window)


def pick_problem(industry: str, problems_by_industry: dict, recent_posts: list, window: int = 10) -> dict | None:
    """Picks a business problem for the given industry, preferring one not
    used in the recent window (tracked via problem_id in topic_history).
    Falls back to the full list if everything's been used recently."""
    candidates = problems_by_industry.get(industry, [])
    if not candidates:
        return None

    recent_ids = {p.get("problem_id") for p in recent_posts[-window:] if p.get("problem_id")}
    fresh = [p for p in candidates if p["id"] not in recent_ids]

    return random.choice(fresh or candidates)
