from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from app.core.config import settings
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS=False,  # Since we're using SSL/TLS on port 465
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    TEMPLATE_FOLDER=Path(__file__).parent.parent / 'templates'
)

class EmailService:
    def __init__(self):
        self.fastmail = FastMail(conf)
        self.jinja_env = Environment(
            loader=FileSystemLoader(conf.TEMPLATE_FOLDER)
        )

    async def send_verification_email(self, email: str, token: str):
        template = self.jinja_env.get_template('verification.html')
        verify_url = f"http://localhost:3000/verify-email?token={token}"
        
        html = template.render(
            verify_url=verify_url,
            support_email=settings.MAIL_FROM
        )

        message = MessageSchema(
            subject="Verify your email address",
            recipients=[email],
            body=html,
            subtype="html"
        )

        await self.fastmail.send_message(message)

    async def send_verification_success(self, email: str):
        template = self.jinja_env.get_template('verification_success.html')
        html = template.render(support_email=settings.MAIL_FROM)

        message = MessageSchema(
            subject="Email verification successful",
            recipients=[email],
            body=html,
            subtype="html"
        )

        await self.fastmail.send_message(message)

    async def send_password_reset_email(self, email: str, token: str):
        """Send password reset email"""
        template = self.jinja_env.get_template('password_reset.html')
        reset_url = f"{settings.FRONTEND_URL}/reset-password/{token}"
        
        html = template.render(
            reset_url=reset_url,
            support_email=settings.MAIL_FROM
        )

        message = MessageSchema(
            subject="Password Reset Request",
            recipients=[email],
            body=html,
            subtype="html"
        )

        await self.fastmail.send_message(message)

    async def send_password_changed_email(self, email: str):
        """Send password changed confirmation email"""
        template = self.jinja_env.get_template('password_changed.html')
        html = template.render(support_email=settings.MAIL_FROM)

        message = MessageSchema(
            subject="Password Changed Successfully",
            recipients=[email],
            body=html,
            subtype="html"
        )

        await self.fastmail.send_message(message)