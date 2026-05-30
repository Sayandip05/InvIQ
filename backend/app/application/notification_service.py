"""
Notification service — handles email notifications for user management.

Layer: Application
Sends welcome emails to newly created users with their credentials.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("smart_inventory.notification")


class NotificationService:
    """Service for sending notifications to users."""

    @staticmethod
    def send_welcome_email(
        to_email: str,
        username: str,
        password: str,
        role: str,
        full_name: Optional[str] = None,
    ) -> bool:
        """
        Send welcome email to newly created user with login credentials.

        Args:
            to_email: User's email address
            username: User's username for login
            password: User's plain text password (sent only once)
            role: User's role (admin, manager, staff, vendor, viewer)
            full_name: User's full name (optional)

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not settings.SMTP_ENABLED:
            logger.info(
                "SMTP disabled - welcome email not sent (to: %s, username: %s)",
                to_email,
                username,
            )
            return False

        if not settings.SMTP_HOST or not settings.SMTP_USER:
            logger.warning("SMTP not configured - welcome email not sent")
            return False

        try:
            # Prepare email content
            subject = f"Welcome to InvIQ - Your {role.title()} Account"
            display_name = full_name or username

            # Role-specific portal URLs
            role_portals = {
                "admin": "/admin/dashboard",
                "manager": "/manager/dashboard",
                "staff": "/staff",
                "vendor": "/vendor",
                "viewer": "/viewer/dashboard",
            }
            portal_url = role_portals.get(role, "/signin")

            # HTML email template
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                              color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .credentials {{ background: white; padding: 20px; border-radius: 8px; 
                                   border-left: 4px solid #667eea; margin: 20px 0; }}
                    .credential-row {{ margin: 10px 0; }}
                    .label {{ font-weight: bold; color: #667eea; }}
                    .value {{ font-family: 'Courier New', monospace; background: #f3f4f6; 
                             padding: 5px 10px; border-radius: 4px; display: inline-block; }}
                    .button {{ display: inline-block; background: #667eea; color: white; 
                              padding: 12px 30px; text-decoration: none; border-radius: 6px; 
                              margin: 20px 0; }}
                    .warning {{ background: #fef3c7; border-left: 4px solid #f59e0b; 
                               padding: 15px; margin: 20px 0; border-radius: 4px; }}
                    .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 30px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🎉 Welcome to InvIQ</h1>
                        <p>Smart Inventory Management System</p>
                    </div>
                    <div class="content">
                        <p>Hi <strong>{display_name}</strong>,</p>
                        
                        <p>Your account has been created successfully! You now have access to InvIQ 
                        as a <strong>{role.title()}</strong>.</p>
                        
                        <div class="credentials">
                            <h3 style="margin-top: 0; color: #667eea;">🔐 Your Login Credentials</h3>
                            <div class="credential-row">
                                <span class="label">Username:</span> 
                                <span class="value">{username}</span>
                            </div>
                            <div class="credential-row">
                                <span class="label">Password:</span> 
                                <span class="value">{password}</span>
                            </div>
                            <div class="credential-row">
                                <span class="label">Role:</span> 
                                <span class="value">{role.title()}</span>
                            </div>
                        </div>
                        
                        <div class="warning">
                            <strong>⚠️ Security Notice:</strong> Please change your password after your first login. 
                            Keep your credentials secure and do not share them with anyone.
                        </div>
                        
                        <div style="text-align: center;">
                            <a href="{settings.FRONTEND_URL or 'http://localhost:5173'}{portal_url}" 
                               class="button">
                                Login to Your Portal
                            </a>
                        </div>
                        
                        <p style="margin-top: 30px;">If you have any questions or need assistance, 
                        please contact your system administrator.</p>
                        
                        <p>Best regards,<br>
                        <strong>InvIQ Team</strong></p>
                    </div>
                    <div class="footer">
                        <p>This is an automated message. Please do not reply to this email.</p>
                        <p>&copy; 2026 InvIQ - Smart Inventory Management System</p>
                    </div>
                </div>
            </body>
            </html>
            """

            # Create email message
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL or settings.SMTP_USER}>"
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(html_content, "html"))

            # Send email with 30-second timeout
            with smtplib.SMTP(
                settings.SMTP_HOST, settings.SMTP_PORT, timeout=30
            ) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(
                    settings.SMTP_FROM_EMAIL or settings.SMTP_USER,
                    to_email,
                    msg.as_string(),
                )

            logger.info(
                "Welcome email sent successfully to %s (username: %s, role: %s)",
                to_email,
                username,
                role,
            )
            return True

        except smtplib.SMTPException as e:
            logger.error("SMTP error sending welcome email to %s: %s", to_email, str(e))
            return False
        except Exception as e:
            logger.error(
                "Unexpected error sending welcome email to %s: %s", to_email, str(e)
            )
            return False
