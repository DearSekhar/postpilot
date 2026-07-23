import json
import os
from typing import Optional, TypedDict

from langgraph.graph import StateGraph, END
from pydantic import ValidationError

from agent.models import PostDraft
from agent import config, diagram_gen, email_render, linkedin_image, llm_provider, token_utils


SYSTEM_PROMPT_TEMPLATE = """You are an assistant that writes short or Medium, sharp LinkedIn posts \
for a working software/AI engineer about AI and Azure topics. You are NOT a marketer — \
avoid buzzwords, hype, and generic "excited to share" openers.

Style preferences you must follow:
- Tone: {tone}
- body_text must be between {min_words} and {max_words} words. Do not fall short of the minimum.
- Structure: {structure_guidance}
- Topics to avoid: {avoid_topics}

Additional notes from past feedback (follow these closely, they reflect real corrections):
{notes}

Respond with ONLY a JSON object, no markdown fences, no text before or after it. \
The entire response must be valid, parseable JSON — this means any paragraph break \
inside body_text must be written as the two characters backslash-n backslash-n (\\n\\n), \
NOT an actual line break. Do not press enter inside string values. Matching exactly this shape:
{{
  "topic": "short topic name",
  "body_text": "the LinkedIn post text",
  "hashtags": ["upto5", "shorttags"],
  "diagram": {{
    "style": "architecture" or "concept",
    "steps": [
      {{"title": "short label", "subtitle": "optional short line"}}
    ]
  }}
}}
Use "architecture" style for topics about a specific Azure/AI service or pipeline \
(2-4 steps, boxes flowing left to right). Use "concept" style for softer, mental-model \
style topics (2-4 steps, simpler labels, no subtitles needed).
"""




USER_PROMPT = "Generate today's post. Pick a topic you have not covered before, related to AI or Azure."


class AgentState(TypedDict, total=False):
    preferences: dict
    draft: Optional[PostDraft]
    diagram_svg: Optional[str]
    html_preview: Optional[str]


def load_preferences(state: AgentState) -> AgentState:
    with open(config.PREFERENCES_PATH, "r") as f:
        prefs = json.load(f)
    return {**state, "preferences": prefs}


def generate_draft(state: AgentState) -> AgentState:
    prefs = state["preferences"]
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        tone=prefs["tone"],
        min_words=prefs["min_words"],
        max_words=prefs["max_words"],
        structure_guidance=prefs["structure_guidance"],
        avoid_topics=", ".join(prefs.get("avoid_topics", [])) or "none",
        notes="\n".join(f"- {n}" for n in prefs.get("notes", [])) or "none yet",
    )        

    

    last_error = None
    for attempt in range(2):  # one retry if the model returns malformed JSON/schema
        try:
            raw = llm_provider.generate_json(system_prompt, USER_PROMPT)
            draft = PostDraft.model_validate(raw)
            return {**state, "draft": draft}
        except (ValueError, ValidationError) as e:
            last_error = e
    raise RuntimeError(f"Failed to generate a valid draft after retries: {last_error}")


def render_diagram(state: AgentState) -> AgentState:
    draft = state["draft"]
    colors = state["preferences"].get("diagram_colors", ["#2563eb", "#0d9488", "#ea580c"])
    svg = diagram_gen.render_svg(draft.diagram, colors)
    return {**state, "diagram_svg": svg}

def upload_diagram(state: AgentState) -> AgentState:
    """Uploads the diagram to LinkedIn now, so the approve token only needs a short URN.
    If LinkedIn isn't configured, skip gracefully — post still works as text-only."""
    if not config.LINKEDIN_ACCESS_TOKEN:
        return {**state, "diagram_image_urn": None}
    try:
        png_bytes = diagram_gen.svg_to_png(state["diagram_svg"])
        urn = linkedin_image.upload_diagram_image(
            png_bytes, config.LINKEDIN_ACCESS_TOKEN, config.LINKEDIN_API_VERSION
        )
        return {**state, "diagram_image_urn": urn}
    except Exception as e:
        print(f"Warning: diagram upload failed, continuing text-only. {e}")
        return {**state, "diagram_image_urn": None}

# def render_preview(state: AgentState) -> AgentState:
#     html = email_render.build_html(state["draft"], state["diagram_svg"])
#     return {**state, "html_preview": html}

# def render_preview(state: AgentState) -> AgentState:
#     draft = state["draft"]
#     approve_url = "#"
#     if config.TOKEN_SIGNING_SECRET:
#         approve_url = token_utils.build_approve_url(
#             draft, config.APPROVE_BASE_URL, config.TOKEN_SIGNING_SECRET
#         )
#     html = email_render.build_html(draft, state["diagram_svg"], approve_url)
#     return {**state, "html_preview": html}    

def render_preview(state: AgentState) -> AgentState:
    draft = state["draft"]
    approve_url = "#"
    if config.TOKEN_SIGNING_SECRET:
        approve_url = token_utils.build_approve_url(
            draft, config.APPROVE_BASE_URL, config.TOKEN_SIGNING_SECRET,
            image_urn=state.get("diagram_image_urn"),
        )
    html = email_render.build_html(draft, state["diagram_svg"], approve_url)
    return {**state, "html_preview": html}

def save_outputs(state: AgentState) -> AgentState:
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(config.OUTPUT_DIR, "draft.json"), "w") as f:
        f.write(state["draft"].model_dump_json(indent=2))
    with open(os.path.join(config.OUTPUT_DIR, "preview.html"), "w") as f:
        f.write(state["html_preview"])
    return state


# def build_graph():
#     graph = StateGraph(AgentState)
#     graph.add_node("load_preferences", load_preferences)
#     graph.add_node("generate_draft", generate_draft)
#     graph.add_node("render_diagram", render_diagram)
#     graph.add_node("render_preview", render_preview)
#     graph.add_node("save_outputs", save_outputs)

#     graph.set_entry_point("load_preferences")
#     graph.add_edge("load_preferences", "generate_draft")
#     graph.add_edge("generate_draft", "render_diagram")
#     graph.add_edge("render_diagram", "render_preview")
#     graph.add_edge("render_preview", "save_outputs")
#     graph.add_edge("save_outputs", END)

#     return graph.compile()

# def build_graph():
#     graph = StateGraph(AgentState)
#     graph.add_node("load_style_preferences", load_preferences)
#     graph.add_node("draft_post_content", generate_draft)
#     graph.add_node("build_diagram_svg", render_diagram)
#     graph.add_node("compose_preview_email", render_preview)
#     graph.add_node("persist_outputs", save_outputs)

#     graph.set_entry_point("load_style_preferences")
#     graph.add_edge("load_style_preferences", "draft_post_content")
#     graph.add_edge("draft_post_content", "build_diagram_svg")
#     graph.add_edge("build_diagram_svg", "compose_preview_email")
#     graph.add_edge("compose_preview_email", "persist_outputs")
#     graph.add_edge("persist_outputs", END)

#     return graph.compile()    

def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("load_style_preferences", load_preferences)
    graph.add_node("draft_post_content", generate_draft)
    graph.add_node("build_diagram_svg", render_diagram)
    graph.add_node("publish_diagram_image", upload_diagram)
    graph.add_node("compose_preview_email", render_preview)
    graph.add_node("persist_outputs", save_outputs)

    graph.set_entry_point("load_style_preferences")
    graph.add_edge("load_style_preferences", "draft_post_content")
    graph.add_edge("draft_post_content", "build_diagram_svg")
    graph.add_edge("build_diagram_svg", "publish_diagram_image")
    graph.add_edge("publish_diagram_image", "compose_preview_email")
    graph.add_edge("compose_preview_email", "persist_outputs")
    graph.add_edge("persist_outputs", END)

    return graph.compile()