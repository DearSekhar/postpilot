"""
Turns a DiagramSpec into a plain, self-contained SVG string.
No external services or system dependencies (like Graphviz) required —
keeps this free and portable to run inside GitHub Actions later.

Supports three layouts:
- "architecture" / "concept": horizontal left-to-right flow (original layout)
- "hierarchy": vertical top-to-bottom flow, for topics that read better as
  a hierarchy/pipeline stacked downward than sideways
Each box can optionally show a small icon (see agent/icons.py) above its
title, chosen by the model from a fixed vocabulary — falls back to no icon
if the model picks something outside that vocabulary.
"""
import textwrap

import cairosvg

from agent.icons import icon_group
from agent.models import DiagramSpec

BOX_W, BOX_H, GAP, MARGIN = 160, 56, 40, 40
ICON_SIZE = 22
TITLE_CHARS_PER_LINE = 16
SUBTITLE_CHARS_PER_LINE = 22
SUBTITLE_LINE_HEIGHT = 13
MAX_SUBTITLE_LINES = 2


def _wrap_subtitle(text: str) -> list[str]:
    if not text:
        return []
    return textwrap.wrap(text, width=SUBTITLE_CHARS_PER_LINE)[:MAX_SUBTITLE_LINES]


def _box_height(step) -> int:
    has_icon = bool(step.icon)
    subtitle_lines = len(_wrap_subtitle(step.subtitle))
    h = BOX_H + (ICON_SIZE + 6 if has_icon else 0)
    if subtitle_lines > 1:
        h += (subtitle_lines - 1) * SUBTITLE_LINE_HEIGHT
    return h


def _render_box(step, x: float, y: float, w: float, h: float, color: str) -> str:
    title = _escape(step.title)
    content_top = y + 20

    icon_svg = ""
    if step.icon:
        icon_x = x + w / 2 - ICON_SIZE / 2
        icon_svg = icon_group(step.icon, icon_x, content_top - 6, ICON_SIZE, color)
        content_top += ICON_SIZE + 4

    title_y = content_top + 12
    subtitle_lines = _wrap_subtitle(step.subtitle)
    subtitle_svg = ""
    for line_idx, line in enumerate(subtitle_lines):
        line_y = title_y + 20 + line_idx * SUBTITLE_LINE_HEIGHT
        subtitle_svg += (
            f'<text x="{x + w/2}" y="{line_y}" text-anchor="middle" '
            f'font-size="11" fill="#475569">{_escape(line)}</text>'
        )

    return f"""
    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8"
          fill="{color}" fill-opacity="0.12" stroke="{color}" stroke-width="1.5"/>
    {icon_svg}
    <text x="{x + w/2}" y="{title_y}" text-anchor="middle"
          font-size="14" font-weight="600" fill="#1e293b">{title}</text>
    {subtitle_svg}
    """


def _render_horizontal(spec: DiagramSpec, colors: list[str]) -> tuple[str, float, float]:
    n = len(spec.steps)
    box_heights = [_box_height(s) for s in spec.steps]
    box_h = max(box_heights)
    total_w = n * BOX_W + (n - 1) * GAP + 2 * MARGIN
    height = (140 if spec.style == "architecture" else 90) + box_h

    boxes, arrows = [], []
    x, y = MARGIN, 70
    for i, step in enumerate(spec.steps):
        color = colors[i % len(colors)]
        boxes.append(_render_box(step, x, y, BOX_W, box_h, color))
        if i < n - 1:
            ax1, ax2, ay = x + BOX_W, x + BOX_W + GAP, y + box_h / 2
            arrows.append(
                f'<line x1="{ax1}" y1="{ay}" x2="{ax2 - 6}" y2="{ay}" '
                f'stroke="#64748b" stroke-width="1.5" marker-end="url(#arrow)"/>'
            )
        x += BOX_W + GAP

    loop_note = ""
    if spec.style == "concept":
        mid_x = total_w / 2
        loop_note = (
            f'<text x="{mid_x}" y="{y + box_h + 40}" text-anchor="middle" '
            f'font-size="12" fill="#64748b">&#8635; repeats each day</text>'
        )

    body = "".join(arrows) + "".join(boxes) + loop_note
    return body, total_w, height


def _render_hierarchy(spec: DiagramSpec, colors: list[str]) -> tuple[str, float, float]:
    n = len(spec.steps)
    box_w = 220
    box_heights = [_box_height(s) for s in spec.steps]
    total_w = box_w + 2 * MARGIN
    x = MARGIN

    boxes, arrows = [], []
    y = 30
    for i, step in enumerate(spec.steps):
        color = colors[i % len(colors)]
        h = box_heights[i]
        boxes.append(_render_box(step, x, y, box_w, h, color))
        if i < n - 1:
            ax = x + box_w / 2
            ay1, ay2 = y + h, y + h + GAP
            arrows.append(
                f'<line x1="{ax}" y1="{ay1}" x2="{ax}" y2="{ay2 - 6}" '
                f'stroke="#64748b" stroke-width="1.5" marker-end="url(#arrow)"/>'
            )
        y += h + GAP

    total_h = y - GAP + 30
    body = "".join(arrows) + "".join(boxes)
    return body, total_w, total_h


def render_svg(spec: DiagramSpec, colors: list[str]) -> str:
    if spec.style == "hierarchy":
        body, total_w, height = _render_hierarchy(spec, colors)
    else:
        body, total_w, height = _render_horizontal(spec, colors)

    return f"""<svg width="{total_w}" height="{height}" viewBox="0 0 {total_w} {height}"
     xmlns="http://www.w3.org/2000/svg" role="img">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6"
            orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#64748b" stroke-width="1.5"
            stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
  </defs>
  {body}
</svg>"""


def svg_to_png(svg_string: str, width: int = 1200) -> bytes:
    """Rasterizes the diagram for LinkedIn upload, which requires an actual image, not SVG."""
    return cairosvg.svg2png(bytestring=svg_string.encode(), output_width=width)


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
