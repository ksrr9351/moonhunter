"""
AI Dump Alert Service - Sends email alerts for 5%+ dump opportunities
Integrates with AI Engine dump detection and email service
"""
import smtplib
import os
import logging
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import re

logger = logging.getLogger(__name__)

DUMP_ALERT_THRESHOLD = 5.0
ALERT_COOLDOWN_HOURS = 6
MAX_EMAILS_PER_RUN = 50


class AIDumpAlertService:
    """
    Service for sending AI-powered dump opportunity email alerts.
    Only sends to users with smart_alerts_enabled and email_notifications_enabled.
    """
    
    def __init__(self, db, dump_detection_engine, market_provider):
        self.db = db
        self.dump_detection_engine = dump_detection_engine
        self.market_provider = market_provider
        
        self.smtp_username = os.environ.get('SMTP_USERNAME')
        self.smtp_password = os.environ.get('SMTP_PASSWORD')
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', 587))
        self.smtp_from_email = os.environ.get('SMTP_FROM_EMAIL') or self.smtp_username
        
        self.sent_alerts_collection = db.ai_dump_alerts_sent
        
        logger.info("AI Dump Alert Service initialized")
    
    def _validate_email(self, email: str) -> bool:
        """Validate email format"""
        if not email:
            return False
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    async def get_eligible_users(self) -> List[Dict]:
        """
        Fetch users eligible for dump alerts.
        Criteria:
        - smart_alerts_enabled = true
        - email_notifications_enabled = true
        - email is verified (exists and valid format)
        """
        try:
            eligible_users = await self.db.alert_settings.find({
                "$or": [
                    {
                        "smart_alerts_enabled": True,
                        "email_notifications_enabled": True,
                        "email": {"$nin": [None, ""]}
                    },
                    {
                        "email_alerts": True,
                        "email": {"$nin": [None, ""]}
                    }
                ]
            }).to_list(None)
            
            verified_users = []
            for user in eligible_users:
                email = user.get('email', '')
                if self._validate_email(email):
                    verified_users.append(user)
                else:
                    logger.debug(f"Skipping invalid email: {email}")
            
            logger.info(f"Found {len(verified_users)} eligible users for dump alerts")
            return verified_users
            
        except Exception as e:
            logger.error(f"Error fetching eligible users: {str(e)}")
            return []
    
    async def check_alert_cooldown(self, user_id: str, symbol: str) -> bool:
        """
        Check if we've already sent an alert for this coin to this user recently.
        Returns True if we should skip (cooldown active), False if we can send.
        """
        try:
            cooldown_cutoff = datetime.now(timezone.utc) - timedelta(hours=ALERT_COOLDOWN_HOURS)
            
            existing = await self.sent_alerts_collection.find_one({
                "user_id": user_id,
                "symbol": symbol,
                "sent_at": {"$gte": cooldown_cutoff.isoformat()}
            })
            
            return existing is not None
            
        except Exception as e:
            logger.error(f"Error checking cooldown: {str(e)}")
            return False
    
    async def record_sent_alert(self, user_id: str, email: str, symbol: str, dump_data: Dict):
        """Record that an alert was sent to prevent duplicates"""
        try:
            await self.sent_alerts_collection.insert_one({
                "user_id": user_id,
                "email": email,
                "symbol": symbol,
                "dump_percentage": dump_data.get("dump_magnitude", 0),
                "ai_recommendation": dump_data.get("recommendation", ""),
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "price_at_alert": dump_data.get("price_usdt", 0)
            })
        except Exception as e:
            logger.error(f"Error recording sent alert: {str(e)}")
    
    def create_dump_alert_email_html(self, dump_data: Dict, app_url: str = "") -> str:
        """
        Create responsive HTML email template for AI dump opportunity.
        Premium Web3 aesthetic with glassmorphism and neon accents.
        Optimized for Gmail, Outlook, Apple Mail.
        """
        symbol = dump_data.get('symbol', 'UNKNOWN')
        name = dump_data.get('name', 'Unknown Coin')
        dump_percentage = abs(dump_data.get('dump_magnitude', dump_data.get('change_1h', 0)))
        current_price = dump_data.get('price_usdt', 0)
        recommendation = dump_data.get('recommendation', 'buy')
        risk_score = dump_data.get('risk_score', 0.5)
        reason = dump_data.get('reason', 'AI detected buying opportunity')
        volume_health = dump_data.get('volume_health', 'healthy')
        change_24h = dump_data.get('change_24h', 0)
        change_7d = dump_data.get('change_7d', 0)
        logo = dump_data.get('logo', '')
        market_cap = dump_data.get('market_cap', 0)
        
        confidence = int((1 - risk_score) * 100)
        confidence = max(50, min(95, confidence))
        
        timestamp = datetime.now(timezone.utc).strftime('%B %d, %Y at %I:%M %p UTC')
        
        if current_price >= 1000:
            price_formatted = f"${current_price:,.2f}"
        elif current_price >= 1:
            price_formatted = f"${current_price:.2f}"
        elif current_price >= 0.01:
            price_formatted = f"${current_price:.4f}"
        else:
            price_formatted = f"${current_price:.6f}"
        
        if market_cap >= 1_000_000_000:
            mcap_formatted = f"${market_cap / 1_000_000_000:.1f}B"
        elif market_cap >= 1_000_000:
            mcap_formatted = f"${market_cap / 1_000_000:.1f}M"
        else:
            mcap_formatted = f"${market_cap:,.0f}"
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>AI Buy Signal - {symbol}</title>
    <!--[if mso]>
    <noscript>
        <xml>
            <o:OfficeDocumentSettings>
                <o:PixelsPerInch>96</o:PixelsPerInch>
            </o:OfficeDocumentSettings>
        </xml>
    </noscript>
    <![endif]-->
    <style type="text/css">
        @media only screen and (max-width: 600px) {{
            .container {{ width: 100% !important; max-width: 100% !important; border-radius: 0 !important; }}
            .content {{ padding: 20px 16px !important; }}
            .header-section {{ padding: 24px 16px !important; }}
            .coin-section {{ padding: 20px 16px !important; }}
            .coin-name {{ font-size: 24px !important; }}
            .coin-price {{ font-size: 18px !important; }}
            .stat-value {{ font-size: 20px !important; }}
            .stat-label {{ font-size: 10px !important; }}
            .signal-text {{ font-size: 32px !important; }}
            .dump-text {{ font-size: 14px !important; }}
            .button-link {{ padding: 16px 32px !important; font-size: 15px !important; }}
            .stats-grid td {{ display: block !important; width: 100% !important; text-align: center !important; padding: 12px 0 !important; border-right: none !important; }}
            .stats-grid tr {{ display: block !important; }}
            .analysis-text {{ font-size: 13px !important; }}
            .footer-section {{ padding: 20px 16px !important; }}
        }}
        @media only screen and (min-width: 601px) and (max-width: 900px) {{
            .container {{ width: 92% !important; }}
            .content {{ padding: 28px !important; }}
        }}
    </style>
</head>
<body style="margin: 0; padding: 0; background-color: #030014; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale;">
    
    <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background: linear-gradient(180deg, #030014 0%, #0a0118 50%, #030014 100%); min-width: 100%;">
        <tr>
            <td align="center" style="padding: 32px 16px;">
                
                <table class="container" width="560" border="0" cellspacing="0" cellpadding="0" style="max-width: 560px; width: 100%; background: linear-gradient(145deg, rgba(15, 10, 40, 0.95) 0%, rgba(8, 5, 25, 0.98) 100%); border-radius: 24px; overflow: hidden; border: 1px solid rgba(139, 92, 246, 0.2); box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(139, 92, 246, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.05);">
                    
                    <!-- Header -->
                    <tr>
                        <td class="header-section" style="padding: 32px 32px 24px 32px; background: linear-gradient(135deg, rgba(139, 92, 246, 0.12) 0%, rgba(6, 182, 212, 0.08) 50%, rgba(139, 92, 246, 0.12) 100%); text-align: center; border-bottom: 1px solid rgba(139, 92, 246, 0.15);">
                            <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td align="center">
                                        <table border="0" cellspacing="0" cellpadding="0">
                                            <tr>
                                                <td style="padding-right: 10px; vertical-align: middle;">
                                                    <div style="width: 44px; height: 44px; background: linear-gradient(135deg, #8B5CF6 0%, #06B6D4 100%); border-radius: 12px; text-align: center; line-height: 44px; font-size: 24px; box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4);">
                                                        &#127769;
                                                    </div>
                                                </td>
                                                <td style="vertical-align: middle;">
                                                    <h1 style="margin: 0; padding: 0; font-size: 26px; font-weight: 800; background: linear-gradient(90deg, #8B5CF6, #06B6D4, #8B5CF6); -webkit-background-clip: text; background-clip: text; color: #8B5CF6; letter-spacing: -0.5px;">
                                                        Moon Hunters
                                                    </h1>
                                                </td>
                                            </tr>
                                        </table>
                                        <p style="margin: 10px 0 0 0; padding: 0; color: rgba(148, 163, 184, 0.9); font-size: 12px; letter-spacing: 2px; text-transform: uppercase; font-weight: 600;">
                                            AI Investment Alert
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Main Content -->
                    <tr>
                        <td class="content" style="padding: 32px;">
                            
                            <!-- Dump Alert Badge -->
                            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 24px;">
                                <tr>
                                    <td align="center">
                                        <table border="0" cellspacing="0" cellpadding="0" style="background: linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(239, 68, 68, 0.05) 100%); border: 1px solid rgba(239, 68, 68, 0.35); border-radius: 100px; box-shadow: 0 0 20px rgba(239, 68, 68, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.05);">
                                            <tr>
                                                <td style="padding: 14px 28px; text-align: center;">
                                                    <span style="font-size: 18px; vertical-align: middle;">&#128165;</span>
                                                    <span class="dump-text" style="color: #F87171; font-size: 15px; font-weight: 700; vertical-align: middle; margin-left: 6px; letter-spacing: 0.5px;">
                                                        {dump_percentage:.1f}% DUMP DETECTED
                                                    </span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Coin Info Card -->
                            <table class="coin-section" width="100%" border="0" cellspacing="0" cellpadding="0" style="background: linear-gradient(145deg, rgba(30, 27, 75, 0.5) 0%, rgba(15, 12, 41, 0.5) 100%); border: 1px solid rgba(139, 92, 246, 0.15); border-radius: 20px; margin-bottom: 20px; box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);">
                                <tr>
                                    <td style="padding: 24px;">
                                        <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                            <tr>
                                                <td width="56" style="vertical-align: top;">
                                                    {"<img src='" + logo + "' width='52' height='52' style='border-radius: 14px; display: block; border: 2px solid rgba(139, 92, 246, 0.3);' alt='" + symbol + "' />" if logo else "<table border='0' cellspacing='0' cellpadding='0'><tr><td style='width: 52px; height: 52px; background: linear-gradient(135deg, #8B5CF6 0%, #06B6D4 100%); border-radius: 14px; text-align: center; vertical-align: middle; font-size: 20px; font-weight: 800; color: #FFFFFF; border: 2px solid rgba(139, 92, 246, 0.3);'>" + symbol[:2] + "</td></tr></table>"}
                                                </td>
                                                <td style="padding-left: 16px; vertical-align: middle;">
                                                    <h2 class="coin-name" style="margin: 0 0 2px 0; padding: 0; color: #FFFFFF; font-size: 28px; font-weight: 800; letter-spacing: -0.5px;">
                                                        {symbol}
                                                    </h2>
                                                    <p style="margin: 0; padding: 0; color: #94A3B8; font-size: 14px; font-weight: 500;">
                                                        {name}
                                                    </p>
                                                </td>
                                                <td align="right" style="vertical-align: middle;">
                                                    <p class="coin-price" style="margin: 0; padding: 0; color: #FFFFFF; font-size: 22px; font-weight: 700;">
                                                        {price_formatted}
                                                    </p>
                                                    <p style="margin: 4px 0 0 0; padding: 0; color: #F87171; font-size: 13px; font-weight: 600;">
                                                        {change_24h:+.2f}% <span style="color: #64748B; font-weight: 400;">(24h)</span>
                                                    </p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- AI Signal Box -->
                            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background: linear-gradient(145deg, rgba(16, 185, 129, 0.12) 0%, rgba(16, 185, 129, 0.04) 100%); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 20px; margin-bottom: 20px; box-shadow: 0 0 30px rgba(16, 185, 129, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.03);">
                                <tr>
                                    <td style="padding: 28px; text-align: center;">
                                        <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                            <tr>
                                                <td align="center">
                                                    <table border="0" cellspacing="0" cellpadding="0" style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(16, 185, 129, 0.1) 100%); border-radius: 16px; padding: 4px;">
                                                        <tr>
                                                            <td style="padding: 12px 16px; text-align: center;">
                                                                <span style="font-size: 28px;">&#129302;</span>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                    <p style="margin: 12px 0 6px 0; padding: 0; color: #94A3B8; font-size: 11px; text-transform: uppercase; letter-spacing: 2px; font-weight: 600;">
                                                        AI Signal
                                                    </p>
                                                    <p class="signal-text" style="margin: 0; padding: 0; color: #10B981; font-size: 36px; font-weight: 800; text-transform: uppercase; letter-spacing: 2px; text-shadow: 0 0 30px rgba(16, 185, 129, 0.5);">
                                                        BUY
                                                    </p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Stats Grid -->
                            <table class="stats-grid" width="100%" border="0" cellspacing="0" cellpadding="0" style="background: linear-gradient(145deg, rgba(30, 27, 75, 0.4) 0%, rgba(15, 12, 41, 0.4) 100%); border: 1px solid rgba(139, 92, 246, 0.12); border-radius: 20px; margin-bottom: 20px; box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.02);">
                                <tr>
                                    <td style="padding: 6px;">
                                        <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                            <tr>
                                                <td width="50%" style="padding: 18px; text-align: center; border-right: 1px solid rgba(139, 92, 246, 0.1);">
                                                    <p class="stat-label" style="margin: 0 0 6px 0; color: #64748B; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">AI Confidence</p>
                                                    <p class="stat-value" style="margin: 0; color: #8B5CF6; font-size: 26px; font-weight: 800;">{confidence}%</p>
                                                </td>
                                                <td width="50%" style="padding: 18px; text-align: center;">
                                                    <p class="stat-label" style="margin: 0 0 6px 0; color: #64748B; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">Volume</p>
                                                    <p class="stat-value" style="margin: 0; color: {'#10B981' if volume_health == 'healthy' else '#FBBF24'}; font-size: 26px; font-weight: 800; text-transform: capitalize;">{volume_health}</p>
                                                </td>
                                            </tr>
                                            <tr>
                                                <td colspan="2" style="padding: 0 18px;"><div style="height: 1px; background: rgba(139, 92, 246, 0.1);"></div></td>
                                            </tr>
                                            <tr>
                                                <td width="50%" style="padding: 18px; text-align: center; border-right: 1px solid rgba(139, 92, 246, 0.1);">
                                                    <p class="stat-label" style="margin: 0 0 6px 0; color: #64748B; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">7D Change</p>
                                                    <p class="stat-value" style="margin: 0; color: {'#10B981' if change_7d >= 0 else '#F87171'}; font-size: 26px; font-weight: 800;">{change_7d:+.1f}%</p>
                                                </td>
                                                <td width="50%" style="padding: 18px; text-align: center;">
                                                    <p class="stat-label" style="margin: 0 0 6px 0; color: #64748B; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">Market Cap</p>
                                                    <p class="stat-value" style="margin: 0; color: #E2E8F0; font-size: 26px; font-weight: 800;">{mcap_formatted}</p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- AI Analysis -->
                            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background: linear-gradient(145deg, rgba(139, 92, 246, 0.08) 0%, rgba(6, 182, 212, 0.05) 100%); border: 1px solid rgba(139, 92, 246, 0.2); border-radius: 16px; margin-bottom: 28px;">
                                <tr>
                                    <td style="padding: 20px 22px;">
                                        <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                            <tr>
                                                <td width="28" style="vertical-align: top; padding-top: 2px;">
                                                    <span style="font-size: 18px;">&#128161;</span>
                                                </td>
                                                <td style="padding-left: 10px;">
                                                    <p class="analysis-text" style="margin: 0; padding: 0; color: #CBD5E1; font-size: 14px; line-height: 1.7;">
                                                        <strong style="color: #A78BFA; font-weight: 700;">AI Analysis:</strong> {reason}
                                                    </p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- CTA Button -->
                            <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td align="center">
                                        <table border="0" cellspacing="0" cellpadding="0" style="width: 100%; border-radius: 14px; background: linear-gradient(135deg, #8B5CF6 0%, #06B6D4 50%, #8B5CF6 100%); background-size: 200% 100%; box-shadow: 0 8px 25px rgba(139, 92, 246, 0.35), 0 4px 10px rgba(6, 182, 212, 0.2);">
                                            <tr>
                                                <td align="center" style="border-radius: 14px;">
                                                    <a class="button-link" href="{app_url}/ai-engine" target="_blank" style="display: block; padding: 18px 48px; color: #FFFFFF; text-decoration: none; font-weight: 700; font-size: 16px; letter-spacing: 0.5px; text-align: center;">
                                                        &#128640; View Opportunity
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
                        <td class="footer-section" style="padding: 24px 32px; background: linear-gradient(180deg, rgba(0, 0, 0, 0.2) 0%, rgba(0, 0, 0, 0.4) 100%); border-top: 1px solid rgba(139, 92, 246, 0.1); text-align: center;">
                            <p style="margin: 0 0 8px 0; padding: 0; color: #64748B; font-size: 12px; line-height: 1.5;">
                                Detected at {timestamp}
                            </p>
                            <p style="margin: 0 0 12px 0; padding: 0; color: #475569; font-size: 11px; line-height: 1.4;">
                                You're receiving this because you enabled AI Dump Alerts
                            </p>
                            <table border="0" cellspacing="0" cellpadding="0" style="margin: 0 auto;">
                                <tr>
                                    <td style="padding-right: 6px; vertical-align: middle;">
                                        <div style="width: 16px; height: 16px; background: linear-gradient(135deg, #8B5CF6, #06B6D4); border-radius: 4px; text-align: center; line-height: 16px; font-size: 10px;">&#127769;</div>
                                    </td>
                                    <td style="vertical-align: middle;">
                                        <p style="margin: 0; padding: 0; color: #475569; font-size: 11px; font-weight: 500;">
                                            Moon Hunters &copy; 2025 | AI-Powered Crypto Intelligence
                                        </p>
                                    </td>
                                </tr>
                            </table>
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
    
    def send_dump_alert_email(self, to_email: str, dump_data: Dict, app_url: str = "") -> bool:
        """
        Send AI dump opportunity alert email.
        Returns True if successful, False otherwise.
        """
        try:
            if not self.smtp_username or not self.smtp_password:
                logger.error("SMTP credentials not configured")
                return False
            
            if not self._validate_email(to_email):
                logger.error(f"Invalid email address: {to_email}")
                return False
            
            symbol = dump_data.get('symbol', 'UNKNOWN')
            dump_percentage = abs(dump_data.get('dump_magnitude', dump_data.get('change_1h', 0)))
            
            if not symbol or symbol == 'UNKNOWN':
                logger.error("Invalid coin data - missing symbol")
                return False
            
            msg = MIMEMultipart('alternative')
            msg['From'] = f"Moon Hunters AI <{self.smtp_from_email}>"
            msg['To'] = to_email
            msg['Subject'] = f"🤖 AI BUY Signal: {symbol} -{dump_percentage:.1f}% Dump Opportunity"
            
            html_content = self.create_dump_alert_email_html(dump_data, app_url)
            
            text_content = f"""
Moon Hunters AI Alert

BUY SIGNAL: {symbol} ({dump_data.get('name', '')})

Dump Detected: -{dump_percentage:.1f}%
Current Price: ${dump_data.get('price_usdt', 0):.6f}
AI Confidence: {int((1 - dump_data.get('risk_score', 0.5)) * 100)}%
Volume Status: {dump_data.get('volume_health', 'healthy')}

AI Analysis: {dump_data.get('reason', '')}

View opportunity: {app_url}/ai-engine

---
Moon Hunters - AI-Powered Crypto Intelligence
"""
            
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            msg.attach(text_part)
            msg.attach(html_part)
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"AI dump alert sent to {to_email} for {symbol} -{dump_percentage:.1f}%")
            return True
            
        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP authentication failed")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error sending dump alert: {str(e)}")
            return False
    
    async def process_dump_alerts(self, app_url: str = "") -> Dict[str, Any]:
        """
        Main processing function for AI dump alerts.
        Called by background task.
        Returns stats about the alert run.
        """
        stats = {
            "dumps_detected": 0,
            "users_fetched": 0,
            "emails_sent": 0,
            "emails_failed": 0,
            "skipped_cooldown": 0,
            "skipped_threshold": 0,
            "started_at": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            coins = await self.market_provider.get_coins_list(100)
            
            if not coins:
                logger.warning("No coins data available for dump detection")
                return stats
            
            analysis = await self.dump_detection_engine.analyze_market(coins)
            dump_opportunities = analysis.get("dump_opportunities", [])
            
            buy_signals = [
                d for d in dump_opportunities 
                if d.get("recommendation") == "buy" and d.get("dump_magnitude", 0) >= DUMP_ALERT_THRESHOLD
            ]
            
            stats["dumps_detected"] = len(buy_signals)
            
            if not buy_signals:
                logger.info("No qualifying dump opportunities (5%+ with buy signal)")
                return stats
            
            logger.info(f"Found {len(buy_signals)} dump opportunities with AI buy signals")
            
            eligible_users = await self.get_eligible_users()

            additional_emails_str = os.environ.get('ADDITIONAL_ALERT_EMAILS', '')
            additional_emails = [e.strip() for e in additional_emails_str.split(',') if e.strip()]
            for extra_email in additional_emails:
                if self._validate_email(extra_email):
                    existing = any(u.get('email') == extra_email for u in eligible_users)
                    if not existing:
                        eligible_users.append({
                            "user_id": f"additional_{extra_email}",
                            "email": extra_email,
                            "smart_alerts_enabled": True,
                            "email_notifications_enabled": True
                        })

            stats["users_fetched"] = len(eligible_users)
            
            if not eligible_users:
                logger.info("No eligible users for dump alerts")
                return stats
            
            emails_sent = 0
            
            for dump in buy_signals:
                symbol = dump.get("symbol")
                dump_magnitude = dump.get("dump_magnitude", 0)
                
                if dump_magnitude < DUMP_ALERT_THRESHOLD:
                    stats["skipped_threshold"] += 1
                    continue
                
                for user in eligible_users:
                    if emails_sent >= MAX_EMAILS_PER_RUN:
                        logger.warning(f"Rate limit reached: {MAX_EMAILS_PER_RUN} emails")
                        break
                    
                    user_id = user.get("user_id", "")
                    email = user.get("email", "")
                    
                    if not email or not self._validate_email(email):
                        continue
                    
                    if await self.check_alert_cooldown(user_id, symbol):
                        stats["skipped_cooldown"] += 1
                        continue
                    
                    if self.send_dump_alert_email(email, dump, app_url):
                        await self.record_sent_alert(user_id, email, symbol, dump)
                        stats["emails_sent"] += 1
                        emails_sent += 1
                    else:
                        stats["emails_failed"] += 1
                
                if emails_sent >= MAX_EMAILS_PER_RUN:
                    break
            
            stats["completed_at"] = datetime.now(timezone.utc).isoformat()
            
            logger.info(f"AI Dump Alert run complete: {stats['emails_sent']} sent, {stats['emails_failed']} failed, {stats['skipped_cooldown']} skipped (cooldown)")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error in dump alert processing: {str(e)}")
            stats["error"] = str(e)
            return stats
    
    async def cleanup_old_records(self, days: int = 7):
        """Clean up old sent alert records"""
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            result = await self.sent_alerts_collection.delete_many({
                "sent_at": {"$lt": cutoff.isoformat()}
            })
            if result.deleted_count > 0:
                logger.info(f"🧹 Cleaned up {result.deleted_count} old alert records")
        except Exception as e:
            logger.error(f"Error cleaning up old records: {str(e)}")


async def run_dump_alert_background_task(
    db,
    dump_detection_engine,
    market_provider,
    app_url: str = "",
    interval_minutes: int = 5
):
    """
    Background task to check for dump opportunities and send alerts.
    Runs every interval_minutes.
    """
    service = AIDumpAlertService(db, dump_detection_engine, market_provider)
    
    logger.info(f"AI Dump Alert background task started (interval: {interval_minutes}m)")
    
    while True:
        try:
            await asyncio.sleep(interval_minutes * 60)
            
            logger.info("Running AI dump alert check...")
            stats = await service.process_dump_alerts(app_url)
            
            if stats.get("emails_sent", 0) > 0:
                logger.info(f"AI dump alerts sent: {stats['emails_sent']}")
            
            await service.cleanup_old_records()
            
        except asyncio.CancelledError:
            logger.info("AI Dump Alert task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in dump alert background task: {str(e)}")
            await asyncio.sleep(60)
