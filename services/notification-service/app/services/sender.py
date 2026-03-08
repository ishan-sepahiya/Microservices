import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from loguru import logger

from app.core.config import settings


async def send_email(to_email: str, subject: str, html_body: str) -> bool:
    """Send an HTML email via SMTP"""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("SMTP not configured — email not sent (logged only)")
        logger.info(f"[EMAIL MOCK] To: {to_email} | Subject: {subject}")
        return True

    try:
        message = MIMEMultipart("alternative")
        message["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.SMTP_USER}>"
        message["To"] = to_email
        message["Subject"] = subject
        message.attach(MIMEText(html_body, "html"))

        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            start_tls=True,
        )
        logger.info(f"Email sent to {to_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


async def send_sms(to_phone: str, message: str) -> bool:
    """Send SMS via Twilio"""
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.warning("Twilio not configured — SMS not sent (logged only)")
        logger.info(f"[SMS MOCK] To: {to_phone} | Message: {message}")
        return True

    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=to_phone,
        )
        logger.info(f"SMS sent to {to_phone}")
        return True
    except Exception as e:
        logger.error(f"Failed to send SMS to {to_phone}: {e}")
        return False
