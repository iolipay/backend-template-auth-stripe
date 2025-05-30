from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from app.core.config import settings
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import logging

logger = logging.getLogger(__name__)

# Configure email settings based on port
if settings.MAIL_PORT == 465:
    # SSL/TLS configuration for port 465
    use_starttls = False
    use_ssl_tls = True
elif settings.MAIL_PORT == 587:
    # STARTTLS configuration for port 587
    use_starttls = True
    use_ssl_tls = False
else:
    # Default to STARTTLS for other ports
    use_starttls = True
    use_ssl_tls = False

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS=use_starttls,
    MAIL_SSL_TLS=use_ssl_tls,
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
        logger.info(f"Email service initialized with {settings.MAIL_SERVER}:{settings.MAIL_PORT}")
        logger.info(f"STARTTLS: {use_starttls}, SSL/TLS: {use_ssl_tls}")

    async def send_verification_email(self, email: str, token: str):
        try:
            template = self.jinja_env.get_template('verification.html')
            verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
            
            logger.info(f"Sending verification email to {email}")
            logger.info(f"Verification URL: {verify_url}")
            
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
            logger.info(f"Verification email sent successfully to {email}")
            
        except Exception as e:
            logger.error(f"Failed to send verification email to {email}: {str(e)}")
            raise Exception(f"Failed to send verification email: {str(e)}")

    async def send_verification_success(self, email: str):
        try:
            template = self.jinja_env.get_template('verification_success.html')
            html = template.render(support_email=settings.MAIL_FROM)

            message = MessageSchema(
                subject="Email verification successful",
                recipients=[email],
                body=html,
                subtype="html"
            )

            await self.fastmail.send_message(message)
            logger.info(f"Verification success email sent to {email}")
            
        except Exception as e:
            logger.error(f"Failed to send verification success email to {email}: {str(e)}")

    async def send_password_reset_email(self, email: str, token: str):
        """Send password reset email"""
        try:
            template = self.jinja_env.get_template('password_reset.html')
            reset_url = f"{settings.FRONTEND_URL}/auth/reset-password/{token}"
            
            logger.info(f"Sending password reset email to {email}")
            
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
            logger.info(f"Password reset email sent successfully to {email}")
            
        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}: {str(e)}")
            raise Exception(f"Failed to send password reset email: {str(e)}")

    async def send_password_changed_email(self, email: str):
        """Send password changed confirmation email"""
        try:
            template = self.jinja_env.get_template('password_changed.html')
            html = template.render(support_email=settings.MAIL_FROM)

            message = MessageSchema(
                subject="Password Changed Successfully",
                recipients=[email],
                body=html,
                subtype="html"
            )

            await self.fastmail.send_message(message)
            logger.info(f"Password changed email sent to {email}")
            
        except Exception as e:
            logger.error(f"Failed to send password changed email to {email}: {str(e)}")

    async def test_email_connection(self):
        """Test email connection and configuration"""
        try:
            logger.info(f"Testing email connection to {settings.MAIL_SERVER}:{settings.MAIL_PORT}")
            logger.info(f"Username: {settings.MAIL_USERNAME}")
            logger.info(f"STARTTLS: {use_starttls}, SSL/TLS: {use_ssl_tls}")
            
            # Try to send a test email to the configured MAIL_FROM address
            message = MessageSchema(
                subject="Email Configuration Test",
                recipients=[settings.MAIL_FROM],
                body="<p>This is a test email to verify email configuration.</p>",
                subtype="html"
            )
            
            await self.fastmail.send_message(message)
            logger.info("Test email sent successfully - email configuration is working")
            return True
            
        except Exception as e:
            logger.error(f"Email configuration test failed: {str(e)}")
            return False