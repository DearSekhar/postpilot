"""
Sends the preview email via Gmail SMTP using an app password.
The diagram is sent as an inline CID attachment (not a base64 data URI) —
Gmail reliably strips data URIs from HTML email but does support CID
inline images referenced via <img src="cid:...">.
"""
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email(
    gmail_address: str,
    app_password: str,
    to_address: str,
    subject: str,
    html_body: str,
    inline_image_bytes: bytes | None = None,
    image_cid: str | None = None,
) -> None:
    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = to_address

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(html_body, "html"))
    msg.attach(alt)

    if inline_image_bytes and image_cid:
        img = MIMEImage(inline_image_bytes)
        img.add_header("Content-ID", f"<{image_cid}>")
        img.add_header("Content-Disposition", "inline", filename="diagram.png")
        msg.attach(img)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, app_password)
        server.sendmail(gmail_address, to_address, msg.as_string())
