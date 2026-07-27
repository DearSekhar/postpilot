"""
HTTP-triggered Azure Function. GET /api/approve?data=...&sig=...

Verifies the signed token (same scheme as agent/token_utils.py), then
publishes the post to LinkedIn via the current /rest/posts endpoint
(the older /v2/ugcPosts is deprecated — do not switch back to it).
"""
import base64
import hashlib
import hmac
import json
import os
import time

import azure.functions as func
import requests

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

SIGNING_SECRET = os.environ["TOKEN_SIGNING_SECRET"]
LINKEDIN_ACCESS_TOKEN = os.environ["LINKEDIN_ACCESS_TOKEN"]
LINKEDIN_API_VERSION = os.environ.get("LINKEDIN_API_VERSION", "202506")


def _sign(payload_b64: str) -> str:
    sig = hmac.new(SIGNING_SECRET.encode(), payload_b64.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode().rstrip("=")


def _pad_b64(s: str) -> str:
    return s + "=" * (-len(s) % 4)


def _get_person_urn() -> str:
    resp = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}"},
        timeout=15,
    )
    resp.raise_for_status()
    member_id = resp.json()["sub"]
    return f"urn:li:person:{member_id}"


# def _publish_post(text: str) -> requests.Response:
#     author_urn = _get_person_urn()
#     return requests.post(
#         "https://api.linkedin.com/rest/posts",
#         headers={
#             "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
#             "Content-Type": "application/json",
#             "X-Restli-Protocol-Version": "2.0.0",
#             "LinkedIn-Version": LINKEDIN_API_VERSION,
#         },
#         json={
#             "author": author_urn,
#             "commentary": text,
#             "visibility": "PUBLIC",
#             "distribution": {
#                 "feedDistribution": "MAIN_FEED",
#                 "targetEntities": [],
#                 "thirdPartyDistributionChannels": [],
#             },
#             "lifecycleState": "PUBLISHED",
#             "isReshareDisabledByAuthor": False,
#         },
#         timeout=30,
#     )


def _publish_post(text: str, image_urn: str | None) -> requests.Response:
    author_urn = _get_person_urn()
    body = {
        "author": author_urn,
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    if image_urn:
        body["content"] = {"media": {"id": image_urn, "altText": "Diagram illustrating the post topic"}}

    return requests.post(
        "https://api.linkedin.com/rest/posts",
        headers={
            "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": LINKEDIN_API_VERSION,
        },
        json=body,
        timeout=30,
    )

def _html(body: str, status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        f"<html><body style='font-family:sans-serif;max-width:500px;margin:60px auto;'>{body}</body></html>",
        mimetype="text/html",
        status_code=status_code,
    )


@app.route(route="approve", methods=["GET"])
def approve(req: func.HttpRequest) -> func.HttpResponse:
    data_b64 = req.params.get("data")
    sig = req.params.get("sig")

    if not data_b64 or not sig:
        return _html("<h2>Missing parameters</h2>", 400)

    expected_sig = _sign(data_b64)
    if not hmac.compare_digest(expected_sig, sig):
        return _html("<h2>Invalid or tampered link</h2>", 403)

    try:
        payload = json.loads(base64.urlsafe_b64decode(_pad_b64(data_b64)))
    except Exception:
        return _html("<h2>Could not read this link's content</h2>", 400)

    if time.time() > payload["expires_at"]:
        return _html("<h2>This link has expired</h2><p>Approve links are valid for 24 hours.</p>", 410)

    
    hashtags_line = " ".join(f"#{h}" for h in payload.get("hashtags", []))
    full_text = f"{payload['body_text']}\n\n{hashtags_line}".strip()
    image_urn = payload.get("image_urn")

    print(f"POSTING — body_text length: {len(payload['body_text'])}, full_text length: {len(full_text)}")
    print(f"POSTING — full_text content: {full_text!r}")

    resp = _publish_post(full_text, image_urn)    

    if resp.status_code == 201:
        return _html("<h2>&#9989; Posted to LinkedIn</h2><p>Check your profile to see it live.</p>")

    return _html(
        f"<h2>&#10060; Failed to post</h2><p>LinkedIn returned {resp.status_code}</p><pre>{resp.text[:500]}</pre>",
        502,
    )
