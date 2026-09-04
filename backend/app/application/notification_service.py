"""
Notification service — handles email templates, business logic, and notifications.

Layer: Application
Prepares branded HTML and plain-text email templates for user onboarding,
low-stock alerts, administrative notifications, and dispatches via the
Infrastructure Email client.
"""

import logging
from typing import Optional, List

from app.core.config import settings
from app.infrastructure.email import smtp_client

logger = logging.getLogger("smart_inventory.notification")


LOGO_URL = "https://raw.githubusercontent.com/Sayandip05/InvIQ/main/frontend/public/logo.png"


class NotificationService:
    """Service for orchestrating notifications to users and administrators."""

    @staticmethod
    def send_welcome_email(
        to_email: str,
        username: str,
        role: str,
        full_name: Optional[str] = None,
        activation_link: Optional[str] = None,
    ) -> bool:
        """
        Send welcome email to newly created user with secure activation / login link.

        Args:
            to_email: User's email address
            username: User's username for login
            role: User's role (admin, staff, vendor)
            full_name: User's full name (optional)
            activation_link: Secure link to set password and activate account (optional)

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        subject = f"Welcome to InvIQ - Your {role.title()} Account"
        display_name = full_name or username

        # Role-specific portal URLs
        role_portals = {
            "admin": "/admin/dashboard",
            "staff": "/staff",
            "vendor": "/vendor",
        }
        portal_url = role_portals.get(role, "/signin")
        target_url = activation_link or f"{settings.FRONTEND_URL or 'http://localhost:5173'}{portal_url}"
        button_label = "Set Password & Activate Account" if activation_link else "Login to Your Portal"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1e293b; margin: 0; padding: 20px; background-color: #f8fafc; }}
                .container {{ max-width: 520px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }}
                .header {{ background: #0f172a; color: #ffffff; padding: 28px 24px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 20px; font-weight: 700; }}
                .header p {{ margin: 4px 0 0; opacity: 0.8; font-size: 13px; }}
                .content {{ padding: 28px 24px; }}
                .greeting {{ font-size: 15px; font-weight: 600; color: #0f172a; margin-bottom: 12px; }}
                .credentials {{ background: #f8fafc; padding: 16px; border-radius: 8px; border: 1px solid #e2e8f0; margin: 18px 0; font-size: 13px; }}
                .credential-row {{ margin: 6px 0; }}
                .label {{ font-weight: 600; color: #475569; }}
                .value {{ font-family: 'Courier New', monospace; background: #ffffff; border: 1px solid #e2e8f0; padding: 3px 8px; border-radius: 4px; display: inline-block; color: #0f172a; font-weight: 600; }}
                .button {{ display: inline-block; background: #0f172a; color: #ffffff !important; padding: 11px 26px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 14px; margin: 18px 0; }}
                .warning {{ background: #f8fafc; border-left: 3px solid #0f172a; padding: 12px 14px; margin: 18px 0; font-size: 12px; color: #475569; border-radius: 0 4px 4px 0; }}
                .footer {{ text-align: center; color: #94a3b8; font-size: 12px; margin-top: 24px; border-top: 1px solid #f1f5f9; padding-top: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <img src="{LOGO_URL}" alt="InvIQ Logo" width="44" height="44" style="width: 44px; height: 44px; object-fit: contain; display: block; margin: 0 auto 10px;" />
                    <h1>InvIQ</h1>
                    <p>Smart Inventory & Warehouse Management</p>
                </div>
                <div class="content">
                    <div class="greeting">Hi {display_name},</div>
                    <p style="font-size: 14px; color: #334155; margin: 0 0 14px 0;">
                        Your account has been created successfully. You now have access to InvIQ as a <strong>{role.title()}</strong>.
                    </p>
                    
                    <div class="credentials">
                        <div class="credential-row">
                            <span class="label">Username:</span> 
                            <span class="value">{username}</span>
                        </div>
                        <div class="credential-row">
                            <span class="label">Role:</span> 
                            <span class="value">{role.title()}</span>
                        </div>
                    </div>
                    
                    <div class="warning">
                        <strong>Security Notice:</strong> Please set your password using the single-use activation link below (valid for 24 hours).
                    </div>
                    
                    <div style="text-align: center;">
                        <a href="{target_url}" class="button">
                            {button_label}
                        </a>
                    </div>
                    
                    <p style="font-size: 13px; color: #64748b; margin-top: 20px;">
                        If you have questions, please reach out to your system administrator.
                    </p>
                    
                    <div class="footer">
                        Best regards,<br>
                        <strong>InvIQ Team</strong>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        return smtp_client.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
        )

    @staticmethod
    def send_low_stock_alert(
        recipients: List[str],
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

        is_critical = alert_status == "CRITICAL"
        status_color = "#111827" if is_critical else "#475569"
        status_label = "CRITICAL" if is_critical else "WARNING"
        subject = f"[InvIQ] [{status_label}] Low Stock Alert: {item_name}"

        dashboard_url = f"{settings.FRONTEND_URL or 'http://localhost:5173'}/admin/inventory"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1e293b; margin: 0; padding: 20px; background-color: #f8fafc; }}
                .container {{ max-width: 520px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }}
                .header {{ background: #0f172a; color: #ffffff; padding: 24px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 20px; font-weight: 700; }}
                .header p {{ margin: 4px 0 0; opacity: 0.8; font-size: 13px; }}
                .content {{ padding: 24px; }}
                .alert-box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-left: 4px solid #0f172a; border-radius: 8px; padding: 16px; margin: 16px 0; }}
                .alert-box h2 {{ margin: 0 0 10px; color: #0f172a; font-size: 16px; }}
                .detail-row {{ display: flex; justify-content: space-between; border-bottom: 1px solid #f1f5f9; padding: 6px 0; font-size: 13px; }}
                .detail-row:last-child {{ border-bottom: none; }}
                .detail-label {{ color: #64748b; font-weight: 600; }}
                .detail-value {{ color: #0f172a; font-weight: 700; }}
                .stock-value {{ color: #0f172a; font-size: 18px; font-weight: 800; }}
                .button {{ display: inline-block; background: #0f172a; color: #ffffff !important; padding: 11px 26px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 14px; margin: 18px 0; }}
                .footer {{ text-align: center; color: #94a3b8; font-size: 12px; margin-top: 20px; border-top: 1px solid #f1f5f9; padding-top: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <img src="{LOGO_URL}" alt="InvIQ Logo" width="44" height="44" style="width: 44px; height: 44px; object-fit: contain; display: block; margin: 0 auto 10px;" />
                    <h1>InvIQ — Stock Alert</h1>
                    <p>Automated Inventory Alert</p>
                </div>
                <div class="content">
                    <div class="alert-box">
                        <h2>{status_label} Stock Alert</h2>
                        <div class="detail-row">
                            <span class="detail-label">Item:</span>
                            <span class="detail-value">{item_name}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Location:</span>
                            <span class="detail-value">{location_name}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Current Stock:</span>
                            <span class="stock-value">{current_stock}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Minimum Required:</span>
                            <span class="detail-value">{min_stock}</span>
                        </div>
                    </div>

                    <p style="font-size: 13px; color: #475569;">Please review inventory levels and initiate a restock order if needed.</p>

                    <div style="text-align: center;">
                        <a href="{dashboard_url}" class="button">View Inventory Dashboard →</a>
                    </div>

                    <div class="footer">
                        <p>&copy; 2026 InvIQ. All rights reserved.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        return smtp_client.send_bulk(
            recipients=recipients,
            subject=subject,
            html_content=html_content,
        )

    @staticmethod
    def send_admin_congratulations_email(
        to_email: str,
        username: str,
        full_name: Optional[str] = None,
        organization_name: Optional[str] = None,
    ) -> bool:
        """
        Send a clean, concise monochromatic (black/white/grey) welcome email to an Admin.

        Args:
            to_email: Admin's email address
            username: Admin username
            full_name: Admin's full name (optional)
            organization_name: Organization name (optional)

        Returns:
            bool: True if sent successfully, False otherwise
        """
        display_name = full_name or username
        sender_contact = "sayandipbar05@gmail.com"
        subject = f"Welcome to InvIQ, {display_name}!"
        org_line = f" for <strong>{organization_name}</strong>" if organization_name else ""
        dashboard_url = f"{settings.FRONTEND_URL or 'http://localhost:5173'}/admin/dashboard"

        org_row = f'<div style="margin: 4px 0;"><strong>Organization:</strong> {organization_name}</div>' if organization_name else ''

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.5; color: #0f172a; margin: 0; padding: 20px; background-color: #f8fafc; }}
                .card {{ max-width: 440px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 28px; border: 1px solid #e2e8f0; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }}
                .header {{ margin-bottom: 20px; text-align: center; }}
                .logo-text {{ font-size: 24px; font-weight: 800; color: #0f172a; margin: 0; letter-spacing: -0.5px; }}
                .greeting {{ font-size: 16px; font-weight: 700; color: #0f172a; margin-bottom: 10px; }}
                .text {{ font-size: 14px; color: #334155; margin-bottom: 16px; line-height: 1.6; }}
                .info-box {{ background: #f8fafc; border-radius: 8px; padding: 14px 16px; margin: 16px 0; font-size: 13px; color: #1e293b; border: 1px solid #e2e8f0; }}
                .btn-wrapper {{ text-align: center; margin: 24px 0 16px; }}
                .btn {{ display: inline-block; background: #0f172a; color: #ffffff !important; padding: 11px 26px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 14px; }}
                .footer {{ text-align: center; font-size: 12px; color: #94a3b8; margin-top: 20px; border-top: 1px solid #f1f5f9; padding-top: 14px; }}
            </style>
        </head>
        <body>
            <div class="card">
                <div class="header">
                    <img src="{LOGO_URL}" alt="InvIQ Logo" width="48" height="48" style="width: 48px; height: 48px; object-fit: contain; display: block; margin: 0 auto 10px;" />
                    <h1 class="logo-text">InvIQ</h1>
                    <p style="margin: 2px 0 0; color: #64748b; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">Smart Inventory Platform</p>
                </div>
                <div class="greeting">Hi {display_name},</div>
                <p class="text">
                    Welcome to <strong>InvIQ</strong>! Your administrator account is now active{org_line}. You can log in to manage inventory, monitor stock health, and access the AI assistant.
                </p>
                <div class="info-box">
                    <div style="margin: 4px 0;"><strong>Username:</strong> {username}</div>
                    <div style="margin: 4px 0;"><strong>Email:</strong> {to_email}</div>
                    {org_row}
                </div>
                <div class="btn-wrapper">
                    <a href="{dashboard_url}" class="btn">Open Admin Dashboard →</a>
                </div>
                <div class="footer">
                    Best regards,<br>
                    <strong>InvIQ Team</strong>
                </div>
            </div>
        </body>
        </html>
        """

        return smtp_client.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            from_email=sender_contact,
            from_name="InvIQ",
            reply_to=sender_contact,
        )

    @staticmethod
    def send_transactional_email(to_email: str, subject: str, body: str) -> bool:
        """Generic helper to dispatch transactional notifications via SMTP."""
        return smtp_client.send_email(
            to_email=to_email,
            subject=subject,
            text_content=body,
        )
