"""
Builds a signed, self-contained, expiring token that encodes the whole post
so the Azure Function can verify + publish without needing shared storage.

Same signing logic is duplicated in the Azure Function (azure-function/function_app.py)
since they're separately deployed units — keep both in sync if this changes.
"""
import base64
import hashlib
import hmac
import json
import time

from agent.models import PostDraft

LINK_LIFETIME_SECONDS = 60 * 60 * 24  # approve link valid for 24 hours


def _sign(payload_b64: str, secret: str) -> str:
    sig = hmac.new(secret.encode(), payload_b64.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode().rstrip("=")


def build_approve_url(draft: PostDraft, base_url: str, signing_secret: str) -> str:
    payload = {
        "body_text": draft.body_text,
        "hashtags": draft.hashtags,
        "expires_at": int(time.time()) + LINK_LIFETIME_SECONDS,
    }
    payload_json = json.dumps(payload, separators=(",", ":")).encode()
    data_b64 = base64.urlsafe_b64encode(payload_json).decode().rstrip("=")
    sig = _sign(data_b64, signing_secret)
    return f"{base_url.rstrip('/')}/approve?data={data_b64}&sig={sig}"
