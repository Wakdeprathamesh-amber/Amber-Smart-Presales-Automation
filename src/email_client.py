import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Dict, Optional, Mapping


class EmailClient:
    def __init__(self, provider: str = "smtp", dry_run: bool = False):
        self.provider = provider
        self.dry_run = dry_run or (os.getenv("EMAIL_DRY_RUN", "true").lower() == "true")
        # SMTP settings (if used in future)
        self.smtp_host = os.getenv("SMTP_HOST")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_pass = os.getenv("SMTP_PASS")
        self.from_email = os.getenv("EMAIL_FROM", "no-reply@example.com")
        self.reply_to = os.getenv("EMAIL_REPLY_TO")

    def send(self, to_email: str, subject: str, body_text: str, body_html: Optional[str] = None,
             extra_headers: Optional[Mapping[str, str]] = None) -> Dict:
        if self.dry_run:
            return {
                "dry_run": True,
                "to": to_email,
                "subject": subject,
                "body_text": body_text[:500],
                "body_html": (body_html or "")[:500]
            }
        # Real SMTP send
        msg = EmailMessage()
        msg["From"] = self.from_email
        msg["To"] = to_email
        msg["Subject"] = subject
        if self.reply_to:
            msg["Reply-To"] = self.reply_to
        # Prefer text; include html as alternative if provided
        if body_html:
            msg.set_content(body_text or "")
            msg.add_alternative(body_html, subtype="html")
        else:
            msg.set_content(body_text or "")

        if extra_headers:
            for k, v in extra_headers.items():
                if v is not None:
                    msg[k] = str(v)

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=20) as server:
                server.starttls(context=context)
                if self.smtp_user and self.smtp_pass:
                    server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            return {"status": "sent", "to": to_email}
        except Exception as e:
            return {"error": str(e)}


