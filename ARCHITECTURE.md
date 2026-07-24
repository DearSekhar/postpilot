# PostPilot — Architecture

## Generation flow (runs when you call `python main.py`)

| Step | Responsibility | File |
|---|---|---|
| `preferences.json` | Style memory — tone, length, structure rules, accumulated feedback notes | `agent/preferences.json` |
| LangGraph agent | Orchestrates the pipeline; calls the LLM (Groq/Gemini) for topic + post text + diagram spec | `agent/graph.py`, `agent/llm_provider.py` |
| Diagram rendering | Turns the LLM's diagram spec into SVG, then rasterizes to PNG | `agent/diagram_gen.py` |
| LinkedIn image upload | Registers an upload slot, PUTs the PNG, gets back `urn:li:image:...` — happens now, not at click time | `agent/linkedin_image.py` |
| Signed token | Packs post text + hashtags + image URN + expiry into a signed, self-contained token (no shared DB needed) | `agent/token_utils.py` |
| Preview email | Builds the HTML preview with the Approve & Post link | `agent/email_render.py` |

## Approval flow (runs when you click "Approve & Post")
| Step | Responsibility | File |
|---|---|---|
| Approve click | Just a GET request to the Function's URL with the token in the query string | (email link) |
| Azure Function | Verifies the HMAC signature and expiry, decodes the token, calls LinkedIn | `azure-function/function_app.py` |
| LinkedIn Posts API | `/rest/posts` — publishes the text, with `content.media.id` referencing the already-uploaded image | LinkedIn (external) |

## Key design decision: why the token carries the image URN, not the image

Uploading the image at *generation* time (not at click time) means the approve link only needs to carry a short string, not image bytes — keeping the whole thing self-contained with no shared database or blob storage required. The image already exists on LinkedIn's side by the time you even see the preview email; clicking Approve just tells LinkedIn "attach that image and publish."

## Known issues / backlog
- Diagram subtitle text can overflow the SVG box width visually (cosmetic, not functional)
- No refresh token from LinkedIn's app tier — `LINKEDIN_ACCESS_TOKEN` needs manual regeneration via `oauth_setup.py` roughly every 60 days
- Not yet automated — currently run manually via `func start` + `python main.py` each session. GitHub Actions scheduling is the planned next phase.
