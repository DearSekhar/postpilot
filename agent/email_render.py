"""
Builds the preview HTML. In Phase 1 this is saved to a local file so you can
review it in a browser. Phase 2 swaps `save_locally` for an actual send,
and turns the button below into a real signed-token approve link.
"""
from agent.models import PostDraft


def build_html(draft: PostDraft, diagram_svg: str) -> str:
    hashtags_line = " ".join(f"#{h.lstrip('#')}" for h in draft.hashtags)
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>LinkedIn post preview</title></head>
<body style="font-family: -apple-system, Arial, sans-serif; max-width: 600px; margin: 40px auto; color: #1e293b;">
  <h2 style="margin-bottom: 4px;">Today's post: {draft.topic}</h2>
  <p style="color: #64748b; font-size: 13px; margin-top: 0;">{draft.word_count} words</p>

  <div style="white-space: pre-wrap; line-height: 1.5; margin: 20px 0;">{draft.body_text}</div>
  <p style="color: #2563eb;">{hashtags_line}</p>

  <div style="margin: 24px 0;">{diagram_svg}</div>

  <a href="#" style="display:inline-block; background:#0d9488; color:white; padding:12px 24px;
     border-radius:6px; text-decoration:none; font-weight:600;">
     Approve &amp; Post (not wired yet — Phase 2)
  </a>
</body>
</html>"""
