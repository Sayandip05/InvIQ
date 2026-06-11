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
from app.core.security import mask_email

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
            role: User's role (admin, manager, staff, vendor)
            full_name: User's full name (optional)

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not settings.SMTP_ENABLED:
            logger.info(
                "SMTP disabled - welcome email not sent (to: %s, username: %s)",
                mask_email(to_email),
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
                mask_email(to_email),
                username,
                role,
            )
            return True

        except smtplib.SMTPException as e:
            logger.error("SMTP error sending welcome email to %s: %s", mask_email(to_email), str(e))
            return False
        except Exception as e:
            logger.error(
                "Unexpected error sending welcome email to %s: %s", mask_email(to_email), str(e)
            )
            return False

    @staticmethod
    def send_low_stock_alert(
        recipients: list[str],
        item_name: str,
        item_id: int,
        location_id: int,
        current_stock: int,
        min_stock: int,
        alert_status: str,
        location_name: str = "Unknown Location",
    ) -> int:
        """
        Broadcast a low-stock / critical-stock alert email to admin/manager recipients.

        Args:
            recipients:    List of email addresses to notify (admins + managers).
            item_name:     Human-readable item name.
            item_id:       Database ID of the item.
            location_id:   Database ID of the location.
            current_stock: Stock level that triggered the alert.
            min_stock:     Configured minimum threshold for this item.
            alert_status:  "WARNING" or "CRITICAL".
            location_name: Human-readable location name (optional, default "Unknown Location").

        Returns:
            int: Number of recipients successfully emailed.
        """
        if not recipients:
            logger.debug("Low-stock alert skipped — no recipients provided")
            return 0

        if not settings.SMTP_ENABLED:
            logger.info(
                "SMTP disabled — low-stock alert not sent (item: %s, status: %s)",
                item_name, alert_status,
            )
            return 0

        if not settings.SMTP_HOST or not settings.SMTP_USER:
            logger.warning("SMTP not configured — low-stock alert not sent (item: %s)", item_name)
            return 0

        # ── Compose message ───────────────────────────────────────────────
        is_critical = alert_status == "CRITICAL"
        status_color  = "#dc2626" if is_critical else "#d97706"  # red : amber
        status_bg     = "#fef2f2" if is_critical else "#fffbeb"
        status_border = "#fca5a5" if is_critical else "#fcd34d"
        status_label  = "🔴 CRITICAL" if is_critical else "⚠️ WARNING"
        subject       = f"[InvIQ] {status_label} Low Stock Alert — {item_name}"

        dashboard_url = (
            f"{settings.FRONTEND_URL or 'http://localhost:5173'}"
            f"/admin/inventory"
        )

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                           color: white; padding: 24px 30px; border-radius: 10px 10px 0 0; }}
                .header h1 {{ margin: 0; font-size: 22px; }}
                .header p  {{ margin: 4px 0 0; opacity: 0.85; font-size: 14px; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .alert-box {{
                    background: {status_bg};
                    border: 1px solid {status_border};
                    border-left: 4px solid {status_color};
                    border-radius: 8px;
                    padding: 20px;
                    margin: 20px 0;
                }}
                .alert-box h2 {{ margin: 0 0 12px; color: {status_color}; font-size: 18px; }}
                .detail-row {{ display: flex; justify-content: space-between;
                               border-bottom: 1px solid #e5e7eb; padding: 8px 0; font-size: 14px; }}
                .detail-row:last-child {{ border-bottom: none; }}
                .detail-label {{ color: #6b7280; font-weight: 600; }}
                .detail-value {{ color: #111827; font-weight: 700; }}
                .stock-value {{ color: {status_color}; font-size: 20px; font-weight: 800; }}
                .button {{ display: inline-block; background: #4f46e5; color: white !important;
                           padding: 12px 28px; text-decoration: none; border-radius: 8px;
                           font-weight: 600; margin: 20px 0; font-size: 14px; }}
                .footer {{ text-align: center; color: #9ca3af; font-size: 12px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>InvIQ — Stock Alert</h1>
                    <p>Automated inventory monitoring notification</p>
                </div>
                <div class="content">
                    <div class="alert-box">
                        <h2>{status_label} — Immediate Attention Required</h2>
                        <div class="detail-row">
                            <span class="detail-label">Item</span>
                            <span class="detail-value">{item_name}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Location</span>
                            <span class="detail-value">{location_name}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Current Stock</span>
                            <span class="stock-value">{current_stock}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Minimum Required</span>
                            <span class="detail-value">{min_stock}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Shortage</span>
                            <span class="detail-value">{max(0, min_stock - current_stock)} units below threshold</span>
                        </div>
                    </div>

                    <p>Please review inventory levels and initiate a requisition or restock order immediately.</p>

                    <div style="text-align: center;">
                        <a href="{dashboard_url}" class="button">View Inventory Dashboard →</a>
                    </div>

                    <p style="color: #6b7280; font-size: 13px; margin-top: 20px;">
                        This alert was triggered automatically when stock for <strong>{item_name}</strong>
                        fell {"to zero or below" if is_critical else "below the minimum threshold"}.
                        Item ID: {item_id} | Location ID: {location_id}
                    </p>
                </div>
                <div class="footer">
                    <p>You are receiving this because you are a manager or admin in InvIQ.</p>
                    <p>&copy; 2026 InvIQ — Smart Inventory Management System</p>
                </div>
            </div>
        </body>
        </html>
        """

        sent_count = 0
        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

                for recipient in recipients:
                    try:
                        msg = MIMEMultipart("alternative")
                        msg["From"]    = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL or settings.SMTP_USER}>"
                        msg["To"]      = recipient
                        msg["Subject"] = subject
                        msg.attach(MIMEText(html_content, "html"))

                        server.sendmail(
                            settings.SMTP_FROM_EMAIL or settings.SMTP_USER,
                            recipient,
                            msg.as_string(),
                        )
                        sent_count += 1
                        logger.info(
                            "Low-stock alert sent to %s (item: %s, status: %s, stock: %d/%d)",
                            mask_email(recipient), item_name, alert_status, current_stock, min_stock,
                        )
                    except smtplib.SMTPException as e:
                        logger.warning(
                            "Failed to send low-stock alert to %s: %s", mask_email(recipient), str(e)
                        )

        except smtplib.SMTPException as e:
            logger.error("SMTP connection error sending low-stock alerts: %s", str(e))
        except Exception as e:
            logger.error("Unexpected error sending low-stock alerts: %s", str(e))

        return sent_count
