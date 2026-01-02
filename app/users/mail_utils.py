import mimetypes
import smtplib
from email.message import EmailMessage
from pathlib import Path


from extensions import db

from .user_model import MailConfig


def load_mail_config():
    config = db.session.scalar(db.select(MailConfig))

    if not config:
        raise RuntimeError("No active mail configuration found")
    return config


def send_email(
    subject: str,
    recipients: list[str],
    cc: list[str],
    bcc: list[str],
    body: str,
    html: str | None = None,
    attachments: list[str | Path] | None = None,
):
    config = load_mail_config()

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.default_sender or config.username
    msg["To"] = ", ".join(recipients)
    msg["Cc"] = cc
    msg["bcc"] = bcc

    if html:
        msg.add_alternative(html, subtype="html")
    else:
        msg.set_content(body)

    if attachments:
        for file_path in attachments:
            path = Path(file_path)

            if not path.exists():
                raise FileNotFoundError(f"Attachment not found: {path}")

            mime_type, encoding = mimetypes.guess_type(path)
            if mime_type is None:
                mime_type = "application/octet-stream"

            maintype, subtype = mime_type.split("/", 1)

            with open(path, "rb") as f:
                msg.add_attachment(
                    f.read(),
                    maintype=maintype,
                    subtype=subtype,
                    filename=path.name,
                )
    with smtplib.SMTP(config.smtp_server, config.smtp_port, timeout=30) as server:
        server.ehlo()
        server.send_message(msg)


def send_email_async(
    app,
    subject: str,
    recipients: list[str],
    cc: list[str],
    bcc: list[str],
    body: str,
    html: str | None = None,
    attachments: list[str] | None = None,
):
    with app.app_context():
        send_email(
            subject=subject,
            recipients=recipients,
            cc=cc,
            bcc=bcc,
            body=body,
            html=html,
            attachments=attachments,
        )
