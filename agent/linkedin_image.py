"""
Uploads the rasterized diagram to LinkedIn's Images API and returns the
resulting image URN. This runs at generation time (not at approve-click
time), so the approve token only needs to carry a short URN string rather
than the whole image.
"""
import requests

USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
IMAGES_INIT_URL = "https://api.linkedin.com/rest/images?action=initializeUpload"


def get_person_urn(access_token: str) -> str:
    resp = requests.get(USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}, timeout=15)
    resp.raise_for_status()
    return f"urn:li:person:{resp.json()['sub']}"


def upload_diagram_image(png_bytes: bytes, access_token: str, api_version: str) -> str:
    """Registers an upload slot, uploads the bytes, returns the image URN (urn:li:image:...)."""
    person_urn = get_person_urn(access_token)

    init_resp = requests.post(
        IMAGES_INIT_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "Linkedin-Version": api_version,
        },
        json={"initializeUploadRequest": {"owner": person_urn}},
        timeout=30,
    )
    init_resp.raise_for_status()
    value = init_resp.json()["value"]
    upload_url = value["uploadUrl"]
    image_urn = value["image"]

    upload_resp = requests.put(
        upload_url,
        data=png_bytes,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=60,
    )
    upload_resp.raise_for_status()

    return image_urn
