"""
Run this ONCE to authorize PostPilot to post on your behalf.
Not part of the daily pipeline — just a manual bootstrap step.

Usage:
    python oauth_setup.py

Requires LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET to already be set
(e.g. via Codespaces secrets, or export them in this shell session first).
"""
import os
import urllib.parse
import requests

REDIRECT_URI = "http://localhost:8000/callback"  # must exactly match what's registered in the Auth tab
SCOPES = "openid profile w_member_social"

CLIENT_ID = os.environ.get("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET")


def build_auth_url() -> str:
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": "postpilot_setup",
    }
    return "https://www.linkedin.com/oauth/v2/authorization?" + urllib.parse.urlencode(params)


def exchange_code_for_tokens(code: str) -> dict:
    resp = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        raise RuntimeError(
            "LINKEDIN_CLIENT_ID / LINKEDIN_CLIENT_SECRET not found in environment. "
            "Make sure your Codespaces secrets are set and you've reloaded the terminal."
        )

    print("1. Open this URL in your browser and approve access:\n")
    print(build_auth_url())
    print(
        "\n2. After approving, LinkedIn will redirect you to a localhost URL that "
        "will fail to load in the browser — that's expected, nothing is listening there."
    )
    print(
        "3. Copy the 'code' value from that URL's address bar "
        "(everything after code= and before &state), and paste it below.\n"
    )

    code = input("Paste the code here: ").strip()

    tokens = exchange_code_for_tokens(code)

    print("\nSuccess. Save these as Codespaces secrets (Settings -> Secrets and variables -> Codespaces):\n")
    print(f"  LINKEDIN_ACCESS_TOKEN = {tokens.get('access_token')}")
    print(f"  (expires in {tokens.get('expires_in')} seconds)")
    if "refresh_token" in tokens:
        print(f"\n  LINKEDIN_REFRESH_TOKEN = {tokens.get('refresh_token')}")
        print(f"  (expires in {tokens.get('refresh_token_expires_in')} seconds)")
    else:
        print(
            "\n  No refresh_token was returned — this app tier may not have refresh "
            "token access. If so, you'll re-run this script when the access token expires."
        )

    print(
        "\nDo NOT commit these anywhere. Add them as Codespaces secrets scoped to "
        "postpilot, the same way you did for GROQ_API_KEY."
    )


if __name__ == "__main__":
    main()
