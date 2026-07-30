"""
Suggests which content category to steer toward next, based on the
declared target mix (content_mix in preferences.json) vs what's actually
been posted recently. This is a hint fed into the prompt, not a hard rule —
the model still makes the final call, this just improves the odds of
actually hitting the target mix over time instead of drifting.
"""
from collections import Counter


def suggest_category(content_mix: dict, recent_posts: list, window: int = 10) -> str | None:
    if not content_mix:
        return None

    recent = recent_posts[-window:]
    if not recent:
        return max(content_mix, key=content_mix.get)

    counts = Counter(p.get("category") for p in recent if p.get("category") in content_mix)
    total = len(recent)

    deficits = {}
    for category, target_pct in content_mix.items():
        actual_pct = (counts.get(category, 0) / total) * 100
        deficits[category] = target_pct - actual_pct

    return max(deficits, key=deficits.get)
