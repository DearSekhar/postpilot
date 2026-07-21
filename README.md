# LinkedIn Daily Post Agent — Phase 1 (generation only)

Generates a topic, post text, and a simple SVG diagram, and saves a preview
you can open in a browser. No email or LinkedIn posting yet — that's Phase 2.

## Setup

```bash
cd linkedin-agent
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:
- Set `LLM_PROVIDER` to `groq` or `gemini`
- Fill in the matching API key (both are free-tier friendly)
  - Groq keys: https://console.groq.com/keys
  - Gemini keys: https://aistudio.google.com/apikey

## Run

```bash
python main.py
```

Then open `output/preview.html` in a browser to see the post + diagram.

## Tuning the style (the "feedback loop")

Open `agent/preferences.json`. This file is read fresh every run and injected
into the system prompt, so any edit changes tomorrow's output immediately.

- Too long? Lower `max_words`.
- Tone off? Adjust the `tone` string.
- Diagram too plain or too busy? Edit `diagram_colors`, or add a note like:
  ```json
  "notes": ["Diagram on 2026-07-21 felt flat — use bolder, more saturated colors"]
  ```
- Anything you noticed about a specific post, add it as a short note. The
  agent reads every note on every future run, so this is how it "learns"
  your preferences without any actual model training.

## Switching providers mid-project

Just change `LLM_PROVIDER` in `.env` — no code changes. Both providers go
through the same `agent/llm_provider.py` abstraction and return the same
JSON shape.

## What's next (Phase 2)

- Real email sending (SMTP or SendGrid) instead of a local HTML file
- Signed, single-use "Approve & Post" link
- Azure Function to verify the click and call the LinkedIn API
- GitHub Actions cron to run this daily instead of by hand
