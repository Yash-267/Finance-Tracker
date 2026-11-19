import json
import logging
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

logger = logging.getLogger("uvicorn.error")


def send_password_reset(email: str, token: str) -> None:
    frontend_url = os.getenv("FRONTEND_URL", "").rstrip("/")
    origin = urlsplit(frontend_url)
    console = os.getenv("PASSWORD_RESET_CONSOLE") == "1"
    link = f"{frontend_url}/reset-password#{urlencode({'token': token})}"

    if console and origin.hostname in {"localhost", "127.0.0.1"} and not os.getenv("RENDER"):
        logger.info("Local password reset link: %s", link)
        return

    api_key = os.getenv("BREVO_API_KEY")
    sender = os.getenv("PASSWORD_RESET_FROM")
    if origin.scheme != "https" or not origin.hostname or not api_key or not sender:
        logger.error("Password reset email requires FRONTEND_URL, BREVO_API_KEY, and PASSWORD_RESET_FROM.")
        return

    payload = {
        "sender": {"email": sender, "name": "Ledger"},
        "to": [{"email": email}],
        "subject": "Reset your Ledger password",
        "textContent": f"Use this link within 30 minutes to set a new password:\n{link}\n\n"
        "If you didn't request this, you can ignore this email.",
    }
    request = Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(payload).encode(),
        headers={"api-key": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10):
            pass
    except HTTPError as exc:
        logger.error("Password reset email provider returned HTTP %s.", exc.code)
    except (URLError, TimeoutError):
        logger.error("Password reset email provider could not be reached.")
