"""
Turns a DiagramSpec into a plain, self-contained SVG string.
No external services or system dependencies (like Graphviz) required —
keeps this free and portable to run inside GitHub Actions later.
"""
import textwrap

import cairosvg

from agent.models import DiagramSpec

BOX_W, BOX_H, GAP, MARGIN = 160, 56, 40, 40
SUBTITLE_CHARS_PER_LINE = 22
SUBTITLE_LINE_HEIGHT = 13
MAX_SUBTITLE_LINES = 2


def _wrap_subtitle(text: str) -> list[str]:
    if not text:
        return []
    return textwrap.wrap(text, width=SUBTITLE_CHARS_PER_LINE)[:MAX_SUBTITLE_LINES]


def render_svg(spec: DiagramSpec, colors: list[str]) -> str:
    n = len(spec.steps)
    total_w = n * BOX_W + (n - 1) * GAP + 2 * MARGIN

    wrapped_subtitles = [_wrap_subtitle(step.subtitle) for step in spec.steps]
    max_lines = max((len(lines) for lines in wrapped_subtitles), default=0)
    box_h = BOX_H if max_lines <= 1 else BOX_H + (max_lines - 1) * SUBTITLE_LINE_HEIGHT

    height = (140 if spec.style == "architecture" else 90) + box_h

    boxes = []
    arrows = []
    x = MARGIN
    y = 70
    for i, step in enumerate(spec.steps):
        color = colors[i % len(colors)]
        title = _escape(step.title)

        subtitle_lines = wrapped_subtitles[i]
        subtitle_svg = ""
        for line_idx, line in enumerate(subtitle_lines):
            line_y = y + 38 + line_idx * SUBTITLE_LINE_HEIGHT
            subtitle_svg += (
                f'<text x="{x + BOX_W/2}" y="{line_y}" text-anchor="middle" '
                f'font-size="11" fill="#475569">{_escape(line)}</text>'
            )

        boxes.append(f"""
        <rect x="{x}" y="{y}" width="{BOX_W}" height="{box_h}" rx="8"
              fill="{color}" fill-opacity="0.12" stroke="{color}" stroke-width="1.5"/>
        <text x="{x + BOX_W/2}" y="{y + 22}" text-anchor="middle"
              font-size="14" font-weight="600" fill="#1e293b">{title}</text>
        {subtitle_svg}
        """)
        if i < n - 1:
            ax1 = x + BOX_W
            ax2 = x + BOX_W + GAP
            ay = y + box_h / 2
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

    return f"""<svg width="{total_w}" height="{height}" viewBox="0 0 {total_w} {height}"
     xmlns="http://www.w3.org/2000/svg" role="img">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6"
            orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#64748b" stroke-width="1.5"
            stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
  </defs>
  {''.join(arrows)}
  {''.join(boxes)}
  {loop_note}
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
