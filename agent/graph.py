import base64
import json
import os
from typing import Optional, TypedDict

from langgraph.graph import StateGraph, END
from pydantic import ValidationError

from agent.models import PostDraft
from agent import config, content_mix, diagram_gen, email_render, email_sender, icons, linkedin_image, llm_provider, news_context, token_utils, topic_history

SYSTEM_PROMPT_TEMPLATE = """You are an assistant that writes short, sharp LinkedIn posts \
for a working software/AI/cloud engineer. You are NOT a marketer — avoid buzzwords, hype, \
and generic "excited to share" openers.

Primary areas of expertise:
{primary_domains}

Target audience:
{target_audience}

Prefer discussing these current AI topics when relevant:
{preferred_ai_topics}

Preferred post styles (pick whichever best fits the topic):
{preferred_post_types}

Tone: {tone}

Hard rules:
- body_text must be between {min_words} and {max_words} words. Do not fall short of the minimum.
- Format body_text as 2-4 short paragraphs separated by a blank line (\\n\\n) — do not write it as one dense block.
- Write objectively about the problem and solution — describe what teams/organizations generally \
face and what the technology offers. Do NOT write in first person as if you personally built or \
experienced this ('I've found', 'in my project', 'we applied this'). No fabricated anecdotes or personal claims.
- Never use these phrases or close variants of them: {avoid_phrases}
{discussion_question_rule}
{business_problem_section}
{news_context_section}

Category: choose exactly one of these labels, matching this post's primary theme:
{category_options}
{category_hint}

Recently published posts — avoid repeating the same topic, category, or industry. If recent \
posts are heavily weighted toward one category or industry, prefer a different one this time:
{recent_posts}

Additional notes from past feedback (follow these closely, they reflect real corrections):
{notes}

Respond with ONLY a JSON object, no markdown fences, no text before or after it. \
The entire response must be valid, parseable JSON — this means any paragraph break \
inside body_text must be written as the two characters backslash-n backslash-n (\\n\\n), \
NOT an actual line break. Do not press enter inside string values. Match exactly this shape:
{{
  "topic": "short topic name",
  "category": "one of the category labels above, exact match",
  "industry": "{industry_field_hint}",
  "business_problem": {{
    "is_new": false,
    "problem": "the business problem this post is built around, in your own words",
    "why_hard": "what makes it genuinely hard for that industry",
    "solution_pattern": "the Azure/AI services and pattern used to solve it"
  }},
  "body_text": "the LinkedIn post text",
  "hashtags": ["upto5", "shorttags"],
  "diagram": {{
    "style": "architecture" or "concept" or "hierarchy",
    "steps": [
      {{"title": "short label", "subtitle": "optional short line", "icon": "optional, see list below"}}
    ]
  }}
}}
Use "architecture" style for topics about a specific Azure/AI service or pipeline \
(2-4 steps, boxes flowing left to right). Use "concept" style for softer, mental-model \
style topics (2-4 steps, simpler labels, no subtitles needed). Use "hierarchy" style \
for topics that read better as a top-down pipeline or layered process (2-4 steps, \
boxes stacked vertically top to bottom) — a good default choice for variety when either \
architecture or hierarchy would fit equally well. Default to \
"{diagram_style_default}" if genuinely unsure.

For each step, optionally set "icon" to the single closest match from this exact list \
(omit the field entirely if nothing fits well — don't force a mismatched icon): \
{icon_names}. For example, a step about end users gets "user", a step about storing data \
gets "database", a step about scanning/inspection gets "camera", a step about a safety or \
compliance check gets "shield", a step about a completed/passed state gets "check", a step \
about a flagged issue gets "alert".
"""

BUSINESS_PROBLEM_TEMPLATE = """
Suggested business problem for this post (a strong starting point — use it unless you have \
a genuinely better, equally specific and real business problem in the same industry in mind):
- Industry: {industry}
- Problem: {problem}
- Why it's genuinely hard: {why_hard}
- Suggested solution direction (Azure/AI services and pattern — you may extend or adjust this \
if a better fit occurs to you): {solution_pattern}

You may either:
(a) Use the suggested problem above — write it in your own words, don't copy these lines \
verbatim, and set "is_new": false in business_problem, echoing back a version of this problem \
in the JSON fields.
(b) Invent a different, comparably specific and realistic business problem in the SAME industry \
({industry}) if you genuinely have a sharper or fresher one — set "is_new": true, and fill in \
"problem" / "why_hard" / "solution_pattern" with your own specific, real-world business problem \
(not a vague topic restatement — it must be as concrete as the example above). Only do this when \
you have something genuinely good; don't invent for the sake of variety alone.

Either way: open the post by grounding it in a real business problem (a concrete, illustrative \
scenario in this industry is good — you don't need a named real company). Explain what makes it \
hard for that industry specifically, not just in generic engineering terms. Then walk through the \
solution with specific Azure/AI services and why they fit. The value of the post is the business \
insight, not a feature announcement — do not frame this as "Microsoft just released X."
"""

USER_PROMPT = (
    "Generate today's post. Pick a topic and category that fits the content mix guidance "
    "and hasn't been covered recently, and build it around the business problem provided "
    "in the system prompt, following all the rules above."
)


class AgentState(TypedDict, total=False):
    preferences: dict
    draft: Optional[PostDraft]
    diagram_svg: Optional[str]
    diagram_image_urn: Optional[str]
    diagram_png_bytes: Optional[bytes]
    html_preview: Optional[str]
    email_html: Optional[str]


def load_preferences(state: AgentState) -> AgentState:
    with open(config.PREFERENCES_PATH, "r") as f:
        prefs = json.load(f)
    return {**state, "preferences": prefs}


def _load_industry_problems() -> dict:
    """Optional file — if it's not present yet, the pipeline just falls back
    to the old generic-topic behavior instead of failing."""
    if not os.path.exists(config.INDUSTRY_PROBLEMS_PATH):
        return {}
    with open(config.INDUSTRY_PROBLEMS_PATH, "r") as f:
        return json.load(f)


def _slugify(text: str, max_words: int = 5) -> str:
    words = "".join(c.lower() if c.isalnum() or c.isspace() else " " for c in text).split()
    return "_".join(words[:max_words]) or "problem"


def _save_new_problem(industry: str, category: str, problem: dict) -> str:
    """Appends a model-invented problem back into industry_problems.json so
    the library grows over time and future runs can dedup and category-match
    against it too. Best-effort — a failure here shouldn't break the run."""
    try:
        data = _load_industry_problems()
        if not data:
            return None
        base_id = _slugify(problem["problem"])
        existing_ids = {p["id"] for p in data.get("problems", {}).get(industry, [])}
        new_id = base_id
        n = 2
        while new_id in existing_ids:
            new_id = f"{base_id}_{n}"
            n += 1
        entry = {
            "id": new_id,
            "category": category,
            "problem": problem["problem"],
            "why_hard": problem["why_hard"],
            "solution_pattern": problem["solution_pattern"],
        }
        data.setdefault("problems", {}).setdefault(industry, []).append(entry)
        with open(config.INDUSTRY_PROBLEMS_PATH, "w") as f:
            json.dump(data, f, indent=2)
        return new_id
    except Exception as e:
        print(f"Warning: failed to save newly invented problem, continuing anyway. {e}")
        return None


def generate_draft(state: AgentState) -> AgentState:
    prefs = state["preferences"]
    recent_posts = topic_history.load_recent_posts()
    mix_targets = prefs.get("content_mix", {})

    category_hint = ""
    if mix_targets:
        suggested = content_mix.suggest_category(mix_targets, recent_posts)
        if suggested:
            category_hint = (
                f"(Suggested category to balance the content mix: {suggested} — "
                f"use this unless the topic genuinely fits better elsewhere)"
            )

    discussion_question_rule = (
        "- End the post with one short, genuine discussion-inviting question (not a generic \"thoughts?\")."
        if prefs.get("discussion_question")
        else "- Do not end with a discussion question."
    )

    # Pick an industry + a concrete business problem to ground the post in.
    industry_data = _load_industry_problems()
    industry_mix = industry_data.get("industry_mix", {})
    problems_by_industry = industry_data.get("problems", {})

    chosen_industry = None
    chosen_problem = None
    business_problem_section = ""
    industry_field_hint = "leave blank if not applicable"

    if industry_mix and problems_by_industry:
        chosen_industry = content_mix.suggest_industry(industry_mix, recent_posts)
        chosen_problem = content_mix.pick_problem(
            chosen_industry, content_mix.suggest_category(mix_targets, recent_posts) if mix_targets else None,
            problems_by_industry, recent_posts,
        )
        if chosen_problem:
            # The problem's own category tag is authoritative from here on —
            # it reflects what the post will actually be about, so the model
            # doesn't get to pick a different category than the content matches.
            locked_category = chosen_problem.get("category")
            if locked_category:
                category_hint = f"(Category is fixed for this post: {locked_category} — use exactly this value)"
            business_problem_section = BUSINESS_PROBLEM_TEMPLATE.format(
                industry=chosen_industry,
                problem=chosen_problem["problem"],
                why_hard=chosen_problem["why_hard"],
                solution_pattern=chosen_problem["solution_pattern"],
            )
            industry_field_hint = chosen_industry
    else:
        business_problem_section = (
            "\nNo curated business problem is available this run — omit the industry and "
            "business_problem fields (leave industry null, business_problem null) and write "
            "a solid post on a topic that fits the category guidance.\n"
        )

    # Optional real-world context (Azure updates, security news) — never a
    # requirement, purely supporting flavor if genuinely relevant. Any
    # failure here is silently ignored; it should never block a post.
    news_context_section = ""
    try:
        effective_category = (chosen_problem.get("category") if chosen_problem else None) or content_mix.suggest_category(mix_targets, recent_posts)
        relevant_news = news_context.get_relevant_context(chosen_industry, effective_category, prefs)
        news_context_section = news_context.format_context_block(relevant_news)
    except Exception as e:
        print(f"Warning: news_context lookup failed, continuing without it. {e}")

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        primary_domains=", ".join(prefs.get("primary_domains", [])) or "general software engineering",
        target_audience=", ".join(prefs.get("target_audience", [])) or "general audience",
        preferred_ai_topics=", ".join(prefs.get("preferred_ai_topics", [])) or "none specified",
        preferred_post_types=", ".join(prefs.get("preferred_post_types", [])) or "none specified",
        tone=prefs.get("tone", "direct, practical"),
        min_words=prefs.get("min_words", 150),
        max_words=prefs.get("max_words", 300),
        avoid_phrases=", ".join(prefs.get("avoid_phrases", [])) or "none",
        discussion_question_rule=discussion_question_rule,
        business_problem_section=business_problem_section,
        news_context_section=news_context_section,
        category_options=", ".join(mix_targets.keys()) if mix_targets else "choose a sensible category",
        category_hint=category_hint,
        recent_posts="\n".join(
            f"- {p['topic']} ({p.get('category', '?')}, industry: {p.get('industry', '?')}, {p.get('date', '?')})"
            for p in recent_posts[-5:]
        )
        or "none yet — this is the first post",
        notes="\n".join(f"- {n}" for n in prefs.get("notes", [])) or "none yet",
        diagram_style_default=prefs.get("diagram_style_default", "concept"),
        icon_names=", ".join(icons.ICON_NAMES),
        industry_field_hint=industry_field_hint,
    )

    last_error = None
    for attempt in range(2):
        try:
            raw = llm_provider.generate_json(system_prompt, USER_PROMPT)
            draft = PostDraft.model_validate(raw)

            problem_id = chosen_problem["id"] if chosen_problem else None
            if draft.business_problem and draft.business_problem.is_new and chosen_industry:
                new_id = _save_new_problem(chosen_industry, draft.category, draft.business_problem.model_dump())
                if new_id:
                    problem_id = new_id

            topic_history.record_post(
                draft.topic,
                draft.category,
                industry=chosen_industry,
                problem_id=problem_id,
            )
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


def render_preview(state: AgentState) -> AgentState:
    draft = state["draft"]
    approve_url = "#"
    if config.TOKEN_SIGNING_SECRET:
        approve_url = token_utils.build_approve_url(
            draft, config.APPROVE_BASE_URL, config.TOKEN_SIGNING_SECRET,
            image_urn=state.get("diagram_image_urn"),
        )
    diagram_png_bytes = diagram_gen.svg_to_png(state["diagram_svg"])
    local_img_src = "data:image/png;base64," + base64.b64encode(diagram_png_bytes).decode()

    html_local = email_render.build_html(draft, local_img_src, approve_url)
    html_email = email_render.build_html(draft, "cid:diagram_image", approve_url)

    return {
        **state,
        "html_preview": html_local,
        "email_html": html_email,
        "diagram_png_bytes": diagram_png_bytes,
    }

def save_outputs(state: AgentState) -> AgentState:
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(config.OUTPUT_DIR, "draft.json"), "w") as f:
        f.write(state["draft"].model_dump_json(indent=2))
    with open(os.path.join(config.OUTPUT_DIR, "preview.html"), "w") as f:
        f.write(state["html_preview"])
    return state



def send_preview_email(state: AgentState) -> AgentState:
    if not (config.GMAIL_ADDRESS and config.GMAIL_APP_PASSWORD and config.RECIPIENT_EMAIL):
        print("Gmail not configured — skipping send, preview saved locally only.")
        return state
    try:
        email_sender.send_email(
            gmail_address=config.GMAIL_ADDRESS,
            app_password=config.GMAIL_APP_PASSWORD,
            to_address=config.RECIPIENT_EMAIL,
            subject=f"Today's LinkedIn post: {state['draft'].topic}",
            html_body=state["email_html"],
            inline_image_bytes=state.get("diagram_png_bytes"),
            image_cid="diagram_image",
        )
        print(f"Preview email sent to {config.RECIPIENT_EMAIL}")
    except Exception as e:
        print(f"Warning: failed to send email, preview still saved locally. {e}")
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
    graph.add_node("deliver_preview_email", send_preview_email)

    graph.set_entry_point("load_style_preferences")
    graph.add_edge("load_style_preferences", "draft_post_content")
    graph.add_edge("draft_post_content", "build_diagram_svg")
    graph.add_edge("build_diagram_svg", "publish_diagram_image")
    graph.add_edge("publish_diagram_image", "compose_preview_email")
    graph.add_edge("compose_preview_email", "persist_outputs")
    graph.add_edge("persist_outputs", "deliver_preview_email")
    graph.add_edge("deliver_preview_email", END)

    return graph.compile()