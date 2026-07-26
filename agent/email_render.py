"""
Builds the preview HTML, both for the locally-saved file and the real email.
Diagram is embedded as a base64 PNG rather than raw SVG — Gmail (and most
email clients) strip <svg> tags out of HTML email entirely.
"""
from agent.models import PostDraft


def build_html(draft: PostDraft, diagram_png_b64: str, approve_url: str) -> str:
    hashtags_line = " ".join(f"#{h.lstrip('#')}" for h in draft.hashtags)
    button_note = "" if approve_url != "#" else " (link not active — TOKEN_SIGNING_SECRET not set)"
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>LinkedIn post preview</title></head>
<body style="font-family: -apple-system, Arial, sans-serif; max-width: 600px; margin: 40px auto; color: #1e293b;">
  <h2 style="margin-bottom: 4px;">Today's post: {draft.topic}</h2>
  <p style="color: #64748b; font-size: 13px; margin-top: 0;">{draft.word_count} words</p>

  <div style="white-space: pre-wrap; line-height: 1.5; margin: 20px 0;">{draft.body_text}</div>
  <p style="color: #2563eb;">{hashtags_line}</p>

  <img src="data:image/png;base64,{diagram_png_b64}" alt="Post diagram"
       style="max-width:100%; margin: 24px 0; display:block;"/>

  <a href="{approve_url}" style="display:inline-block; background:#0d9488; color:white; padding:12px 24px;
     border-radius:6px; text-decoration:none; font-weight:600;">
     Approve &amp; Post{button_note}
  </a>
</body>
</html>"""
