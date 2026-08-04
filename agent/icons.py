"""
A small, hand-drawn icon set (24x24 viewBox, stroke-based) used to make
diagram boxes more visually distinct than plain rectangles. Deliberately
hand-authored rather than pulled from a third-party icon library — keeps
this dependency-free and free of any licensing question.

Each value is inner SVG markup only (no outer <svg> tag). Default stroke
is "currentColor" so the icon automatically picks up whatever color is
set on its wrapping <g>, matching the box's accent color.
"""

ICONS = {
    "user": (
        '<circle cx="12" cy="8" r="4"/>'
        '<path d="M4 20c0-4.4 3.6-8 8-8s8 3.6 8 8"/>'
    ),
    "database": (
        '<ellipse cx="12" cy="6" rx="8" ry="3"/>'
        '<path d="M4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6"/>'
        '<path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>'
    ),
    "cloud": (
        '<path d="M7 18h10a4 4 0 0 0 .5-8 5.5 5.5 0 0 0-10.6-1.5A4.5 4.5 0 0 0 7 18z"/>'
    ),
    "camera": (
        '<rect x="3" y="7" width="18" height="13" rx="2"/>'
        '<path d="M8 7l1.5-3h5L16 7"/>'
        '<circle cx="12" cy="13.5" r="3.5"/>'
    ),
    "shield": (
        '<path d="M12 3l7 3v6c0 5-3.5 7.5-7 9-3.5-1.5-7-4-7-9V6l7-3z"/>'
    ),
    "check": (
        '<path d="M4 12.5l5 5L20 6"/>'
    ),
    "alert": (
        '<path d="M12 3L2 21h20L12 3z"/>'
        '<line x1="12" y1="9" x2="12" y2="14"/>'
        '<circle cx="12" cy="17" r="0.8" fill="currentColor" stroke="none"/>'
    ),
    "server": (
        '<rect x="3" y="4" width="18" height="6" rx="1.5"/>'
        '<rect x="3" y="14" width="18" height="6" rx="1.5"/>'
        '<circle cx="7" cy="7" r="0.8" fill="currentColor" stroke="none"/>'
        '<circle cx="7" cy="17" r="0.8" fill="currentColor" stroke="none"/>'
    ),
    "mail": (
        '<rect x="3" y="5" width="18" height="14" rx="2"/>'
        '<path d="M3 7l9 6 9-6"/>'
    ),
    "chart": (
        '<line x1="4" y1="20" x2="4" y2="4"/>'
        '<line x1="4" y1="20" x2="21" y2="20"/>'
        '<rect x="7" y="12" width="3" height="8"/>'
        '<rect x="12" y="8" width="3" height="12"/>'
        '<rect x="17" y="14" width="3" height="6"/>'
    ),
    "factory": (
        '<path d="M3 21V11l5 3v-3l5 3V8l5 3v10H3z"/>'
        '<line x1="3" y1="21" x2="21" y2="21"/>'
    ),
    "hospital": (
        '<rect x="4" y="4" width="16" height="16" rx="2"/>'
        '<line x1="12" y1="8" x2="12" y2="16"/>'
        '<line x1="8" y1="12" x2="16" y2="12"/>'
    ),
    "gear": (
        '<circle cx="12" cy="12" r="9"/>'
        '<circle cx="12" cy="12" r="3"/>'
        '<line x1="21" y1="12" x2="23" y2="12"/>'
        '<line x1="16.5" y1="4.2" x2="17.5" y2="2.5"/>'
        '<line x1="7.5" y1="4.2" x2="6.5" y2="2.5"/>'
        '<line x1="3" y1="12" x2="1" y2="12"/>'
        '<line x1="7.5" y1="19.8" x2="6.5" y2="21.5"/>'
        '<line x1="16.5" y1="19.8" x2="17.5" y2="21.5"/>'
    ),
    "lock": (
        '<rect x="5" y="11" width="14" height="10" rx="2"/>'
        '<path d="M8 11V7a4 4 0 0 1 8 0v4"/>'
    ),
    "search": (
        '<circle cx="10" cy="10" r="6"/>'
        '<line x1="15" y1="15" x2="20" y2="20"/>'
    ),
    "package": (
        '<path d="M3 8l9-5 9 5-9 5-9-5z"/>'
        '<path d="M3 8v9l9 5 9-5V8"/>'
        '<line x1="12" y1="13" x2="12" y2="22"/>'
    ),
}

ICON_NAMES = sorted(ICONS.keys())


def icon_group(name: str, x: float, y: float, size: float, color: str) -> str:
    """Returns a positioned, scaled, colored <g> for the given icon name.
    Assumes the icon is defined on a 24x24 grid; empty string if unknown."""
    markup = ICONS.get(name)
    if not markup:
        return ""
    scale = size / 24
    return (
        f'<g transform="translate({x},{y}) scale({scale})" '
        f'fill="none" stroke="{color}" stroke-width="1.8" '
        f'stroke-linecap="round" stroke-linejoin="round">{markup}</g>'
    )
