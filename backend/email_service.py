"""
Email Alert Service for Moon Hunters
Sends real-time alerts for crypto market movements via Gmail SMTP
"""
import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Dict, Optional
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

logger = logging.getLogger(__name__)

class EmailAlertService:
    """Email service for sending crypto movement alerts"""
    
    def __init__(self):
        self.smtp_username = os.environ.get('SMTP_USERNAME')
        self.smtp_password = os.environ.get('SMTP_PASSWORD')
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', 587))
        self.smtp_from_email = os.environ.get('SMTP_FROM_EMAIL') or self.smtp_username
        
        if not self.smtp_username or not self.smtp_password:
            logger.warning("SMTP credentials not configured")
    
    def create_alert_email_html(self, movement: Dict) -> str:
        """Create Gmail-compatible HTML email template for movement alert"""
        symbol = movement.get('symbol', 'UNKNOWN')
        name = movement.get('name', 'Unknown Coin')
        change_percent = movement.get('price_change_percent', 0)
        current_price = movement.get('current_price', 0)
        previous_price = movement.get('previous_price', 0)
        movement_type = movement.get('movement_type', 'movement')
        timestamp = movement.get('timestamp', datetime.now(timezone.utc).isoformat())
        
        # Format timestamp
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            formatted_time = dt.strftime('%B %d, %Y at %I:%M %p UTC')
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse timestamp: {e}")
            formatted_time = timestamp
        
        # Color and emoji based on movement type
        if movement_type == 'pump':
            color = '#32ff7e'
            emoji = '🚀'
            direction = 'UP'
            bg_color = 'rgba(50, 255, 126, 0.1)'
            border_color = 'rgba(50, 255, 126, 0.3)'
        else:
            color = '#ff4d4d'
            emoji = '💥'
            direction = 'DOWN'
            bg_color = 'rgba(255, 77, 77, 0.1)'
            border_color = 'rgba(255, 77, 77, 0.3)'
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Moon Hunters Alert</title>
    <style type="text/css">
        @media only screen and (max-width: 600px) {{
            .container {{ width: 100% !important; max-width: 100% !important; }}
            .content {{ padding: 20px !important; }}
            .price-change {{ font-size: 56px !important; line-height: 1.2 !important; }}
            .button {{ padding: 18px 24px !important; font-size: 15px !important; }}
        }}
    </style>
</head>
<body style="margin: 0; padding: 0; background-color: #0a0a0a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
    <!-- Outer wrapper -->
    <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #0a0a0a; min-width: 100%;">
        <tr>
            <td align="center" style="padding: 30px 15px;">
                
                <!-- Main Container -->
                <table class="container" width="600" border="0" cellspacing="0" cellpadding="0" style="max-width: 600px; width: 100%; background-color: #1a1a2e; border-radius: 16px; overflow: hidden;">
                    
                    <!-- Header Section -->
                    <tr>
                        <td style="padding: 30px 30px 24px 30px; background-color: #111827; text-align: center; border-bottom: 1px solid rgba(255, 255, 255, 0.08);">
                            <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td align="center">
                                        <h1 style="margin: 0; padding: 0; font-size: 32px; font-weight: 700; color: #00FFD1; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                                            Moon Hunters
                                        </h1>
                                        <p style="margin: 10px 0 0 0; padding: 0; color: #9CA3AF; font-size: 15px; line-height: 1.4;">
                                            Real-Time Crypto Market Alerts
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Alert Badge -->
                    <tr>
                        <td class="content" style="padding: 30px;">
                            <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td align="center">
                                        <table border="0" cellspacing="0" cellpadding="0" style="background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 10px;">
                                            <tr>
                                                <td style="padding: 14px 28px; text-align: center;">
                                                    <span style="font-size: 28px; vertical-align: middle;">{emoji}</span>
                                                    <span style="color: {color}; font-size: 17px; font-weight: 700; vertical-align: middle; margin-left: 10px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                                                        FAST {direction} DETECTED
                                                    </span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Coin Info Card -->
                    <tr>
                        <td class="content" style="padding: 0 30px 24px 30px;">
                            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 12px;">
                                <tr>
                                    <td style="padding: 26px 28px;">
                                        <h2 style="margin: 0 0 10px 0; padding: 0; color: #FFFFFF; font-size: 28px; font-weight: 700; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                                            {symbol}
                                        </h2>
                                        <p style="margin: 0; padding: 0; color: #D1D5DB; font-size: 16px; line-height: 1.4;">
                                            {name}
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Price Change Card -->
                    <tr>
                        <td class="content" style="padding: 0 30px 24px 30px;">
                            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 12px;">
                                <tr>
                                    <td style="padding: 32px 28px; text-align: center;">
                                        <div class="price-change" style="font-size: 64px; font-weight: 700; color: {color}; line-height: 1; margin-bottom: 12px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                                            {change_percent:+.2f}%
                                        </div>
                                        <p style="margin: 0; padding: 0; color: #E5E7EB; font-size: 15px; font-weight: 500;">
                                            Price Change
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Price Details Card -->
                    <tr>
                        <td class="content" style="padding: 0 30px 24px 30px;">
                            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 12px;">
                                <tr>
                                    <td style="padding: 24px 28px;">
                                        
                                        <!-- Previous Price Row -->
                                        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 16px;">
                                            <tr>
                                                <td style="padding: 0; color: #E5E7EB; font-size: 15px; font-weight: 500; vertical-align: middle;">
                                                    Previous Price:
                                                </td>
                                                <td align="right" style="padding: 0; color: #FFFFFF; font-size: 16px; font-weight: 600; vertical-align: middle;">
                                                    ${previous_price:.4f}
                                                </td>
                                            </tr>
                                        </table>
                                        
                                        <!-- Current Price Row -->
                                        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 16px;">
                                            <tr>
                                                <td style="padding: 0; color: #E5E7EB; font-size: 15px; font-weight: 500; vertical-align: middle;">
                                                    Current Price:
                                                </td>
                                                <td align="right" style="padding: 0; color: {color}; font-size: 16px; font-weight: 600; vertical-align: middle;">
                                                    ${current_price:.4f}
                                                </td>
                                            </tr>
                                        </table>
                                        
                                        <!-- Detected At Row -->
                                        <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                            <tr>
                                                <td style="padding: 0; color: #E5E7EB; font-size: 15px; font-weight: 500; vertical-align: middle;">
                                                    Detected At:
                                                </td>
                                                <td align="right" style="padding: 0; color: #FFFFFF; font-size: 16px; font-weight: 600; vertical-align: middle;">
                                                    {formatted_time}
                                                </td>
                                            </tr>
                                        </table>
                                        
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- CTA Button -->
                    <tr>
                        <td class="content" style="padding: 0 30px 30px 30px;">
                            <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td align="center">
                                        <table border="0" cellspacing="0" cellpadding="0">
                                            <tr>
                                                <td align="center" class="button" style="border-radius: 10px; background: linear-gradient(135deg, #00FFD1 0%, #8A2BE2 100%);">
                                                    <a href="/top-gainers" target="_blank" style="display: inline-block; padding: 18px 40px; color: #FFFFFF; text-decoration: none; font-weight: 700; font-size: 16px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                                                        View Live Dashboard
                                                    </a>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 24px 30px; background-color: #111827; border-top: 1px solid rgba(255, 255, 255, 0.08); text-align: center;">
                            <p style="margin: 0 0 10px 0; padding: 0; color: #9CA3AF; font-size: 14px; line-height: 1.5;">
                                You're receiving this because you enabled Smart Alerts
                            </p>
                            <p style="margin: 0; padding: 0; color: #6B7280; font-size: 13px; line-height: 1.4;">
                                Moon Hunters © 2025 | AI-Powered Crypto Intelligence
                            </p>
                        </td>
                    </tr>
                    
                </table>
                
            </td>
        </tr>
    </table>
</body>
</html>
"""
        return html
    
    def send_alert_email(
        self,
        to_email: str,
        movement: Dict,
        user_threshold: int
    ) -> bool:
        """
        Send alert email for detected movement
        
        Args:
            to_email: Recipient email address
            movement: Movement data dict
            user_threshold: User's configured threshold
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            if not self.smtp_username or not self.smtp_password:
                logger.error("SMTP credentials not configured")
                return False
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"Moon Hunters Alerts <{self.smtp_from_email}>"
            msg['To'] = to_email
            
            symbol = movement.get('symbol', 'UNKNOWN')
            change = movement.get('price_change_percent', 0)
            movement_type = movement.get('movement_type', 'movement')
            
            # Subject with emoji
            emoji = '🚀' if movement_type == 'pump' else '💥'
            msg['Subject'] = f"{emoji} {symbol} Alert: {change:+.2f}% Movement Detected!"
            
            # Create HTML content
            html_content = self.create_alert_email_html(movement)
            
            # Attach HTML
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email via Gmail SMTP
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Enable TLS encryption
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Alert email sent to {to_email} for {symbol} {change:+.2f}%")
            return True
            
        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP authentication failed - check credentials")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error sending alert email: {str(e)}")
            return False


# Singleton instance
email_service = EmailAlertService()
