"""
Thin abstraction so the rest of the agent doesn't care which LLM is behind it.
Swap providers by changing LLM_PROVIDER in .env — no code changes needed.
"""
import json
import re
import requests
from agent import config


def _strip_json_fences(text: str) -> str:
    """Models sometimes wrap JSON in ```json ... ``` — strip that before parsing."""
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    return text


def _call_groq(system_prompt: str, user_prompt: str) -> str:
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"},
        json={
            "model": config.GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.8,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _call_gemini(system_prompt: str, user_prompt: str) -> str:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{config.GEMINI_MODEL}:generateContent?key={config.GEMINI_API_KEY}"
    )
    resp = requests.post(
        url,
        json={
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {"temperature": 0.8},
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]

def _escape_newlines_in_strings(text: str) -> str:
    """
    Models sometimes emit literal line breaks inside a JSON string value
    (e.g. for paragraph breaks) instead of the escaped \n JSON requires.
    Walk the text tracking whether we're inside a quoted string, and fix
    only newlines found there.
    """
    result = []
    in_string = False
    escape = False
    for ch in text:
        if escape:
            result.append(ch)
            escape = False
            continue
        if ch == "\\":
            result.append(ch)
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue
        if in_string and ch == "\n":
            result.append("\\n")
            continue
        if in_string and ch == "\r":
            continue
        result.append(ch)
    return "".join(result)


def generate_json(system_prompt: str, user_prompt: str) -> dict:
    """Call the configured provider and parse the response as JSON."""
    if config.LLM_PROVIDER == "groq":
        raw = _call_groq(system_prompt, user_prompt)
    elif config.LLM_PROVIDER == "gemini":
        raw = _call_gemini(system_prompt, user_prompt)
    else:
        raise RuntimeError(f"Unknown provider: {config.LLM_PROVIDER}")

    cleaned = _strip_json_fences(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    try:
        return json.loads(_escape_newlines_in_strings(cleaned))
    except json.JSONDecodeError as e:
        raise ValueError(f"Model did not return valid JSON:\n{raw}") from e