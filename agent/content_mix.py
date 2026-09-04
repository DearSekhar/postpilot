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


# Default target mix for diagram layout variety. Deliberately not weighted
# evenly — "architecture" was the model's default go-to before this existed,
# so hierarchy/concept get a slightly larger target share to actively pull
# variety in, not just prevent further drift.
DEFAULT_DIAGRAM_STYLE_MIX = {"architecture": 30, "hierarchy": 40, "concept": 30}


def suggest_diagram_style(recent_posts: list, style_mix: dict | None = None, window: int = 10) -> str | None:
    return suggest_weighted(style_mix or DEFAULT_DIAGRAM_STYLE_MIX, recent_posts, field="diagram_style", window=window)


def pick_problem(industry: str, category: str, problems_by_industry: dict, recent_posts: list, window: int = 30) -> dict | None:
    """Picks a business problem for the given industry, strongly preferring
    one not used recently — freshness is checked over a wide window (30 by
    default, deliberately wider than the category/industry mix window) since
    an exact problem repeat is worse than a slight category mismatch.

    Fallback chain (each step only runs if the previous finds nothing):
    1. same industry + matching category + not recently used
    2. same industry + ANY category + not recently used   <- freshness beats category match
    3. same industry + matching category, reuse allowed   <- last resort within category
    4. same industry, any, reuse allowed                  <- true last resort (catalog exhausted)

    Returns the chosen problem with an extra "_is_reuse" key (True only if
    steps 3/4 fired) so the caller can tell the model it's revisiting a
    problem and should find a genuinely different angle.
    """
    all_candidates = problems_by_industry.get(industry, [])
    if not all_candidates:
        return None

    recent_ids = {p.get("problem_id") for p in recent_posts[-window:] if p.get("problem_id")}

    category_matches = [p for p in all_candidates if p.get("category") == category]
    fresh_category_matches = [p for p in category_matches if p["id"] not in recent_ids]
    if fresh_category_matches:
        return {**random.choice(fresh_category_matches), "_is_reuse": False}

    fresh_any = [p for p in all_candidates if p["id"] not in recent_ids]
    if fresh_any:
        return {**random.choice(fresh_any), "_is_reuse": False}

    choice = random.choice(category_matches or all_candidates)
    return {**choice, "_is_reuse": True}
    """Picks a business problem for the given industry that matches the
    suggested category where possible, preferring one not used in the
    recent window (tracked via problem_id in topic_history).

    Fallback chain (each step only runs if the previous finds nothing):
    1. same industry + matching category + not recently used
    2. same industry + matching category (ignore recency)
    3. same industry, any category + not recently used
    4. same industry, any category (ignore recency)
    """
    all_candidates = problems_by_industry.get(industry, [])
    if not all_candidates:
        return None

    recent_ids = {p.get("problem_id") for p in recent_posts[-window:] if p.get("problem_id")}

    category_matches = [p for p in all_candidates if p.get("category") == category]

    fresh_category_matches = [p for p in category_matches if p["id"] not in recent_ids]
    if fresh_category_matches:
        return random.choice(fresh_category_matches)
    if category_matches:
        return random.choice(category_matches)

    fresh_any = [p for p in all_candidates if p["id"] not in recent_ids]
    return random.choice(fresh_any or all_candidates)
