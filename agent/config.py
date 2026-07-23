"""Central place for environment/config so switching providers is a one-line change."""
import os
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

TOKEN_SIGNING_SECRET = os.getenv("TOKEN_SIGNING_SECRET")
APPROVE_BASE_URL = os.getenv("APPROVE_BASE_URL", "http://localhost:7071/api")

PREFERENCES_PATH = os.path.join(os.path.dirname(__file__), "preferences.json")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")

LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_API_VERSION = os.getenv("LINKEDIN_API_VERSION", "202601")

def validate() -> None:
    """Fail fast with a clear message instead of a confusing API error later."""
    if LLM_PROVIDER == "groq" and not GROQ_API_KEY:
        raise RuntimeError("LLM_PROVIDER=groq but GROQ_API_KEY is not set in .env")
    if LLM_PROVIDER == "gemini" and not GEMINI_API_KEY:
        raise RuntimeError("LLM_PROVIDER=gemini but GEMINI_API_KEY is not set in .env")
    if LLM_PROVIDER not in ("groq", "gemini"):
        raise RuntimeError(f"Unknown LLM_PROVIDER '{LLM_PROVIDER}' — use 'groq' or 'gemini'")
