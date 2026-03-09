"""
Push Notification Service
Handles browser push notifications for price alerts
"""
import os
import json
import logging
from pywebpush import webpush, WebPushException
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class PushNotificationService:
    def __init__(self, db):
        self.db = db
        self.vapid_private_key = os.environ.get('VAPID_PRIVATE_KEY')
        self.vapid_public_key = os.environ.get('VAPID_PUBLIC_KEY')
        self.vapid_email = os.environ.get('VAPID_EMAIL', 'mailto:admin@moonhunters.app')
        
        if not self.vapid_private_key or not self.vapid_public_key:
            logger.warning("VAPID keys not configured - push notifications disabled")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("Push Notification Service initialized")
    
    async def save_subscription(self, user_id: str, subscription: Dict[str, Any]) -> bool:
        """Save a push subscription for a user"""
        try:
            await self.db.push_subscriptions.update_one(
                {"user_id": user_id, "endpoint": subscription.get("endpoint")},
                {
                    "$set": {
                        "user_id": user_id,
                        "endpoint": subscription.get("endpoint"),
                        "keys": subscription.get("keys"),
                        "active": True
                    }
                },
                upsert=True
            )
            logger.info(f"📱 Saved push subscription for user {user_id[:10]}...")
            return True
        except Exception as e:
            logger.error(f"Error saving push subscription: {e}")
            return False
    
    async def remove_subscription(self, user_id: str, endpoint: Optional[str] = None) -> bool:
        """Remove push subscription(s) for a user"""
        try:
            if endpoint:
                await self.db.push_subscriptions.update_one(
                    {"user_id": user_id, "endpoint": endpoint},
                    {"$set": {"active": False}}
                )
            else:
                await self.db.push_subscriptions.update_many(
                    {"user_id": user_id},
                    {"$set": {"active": False}}
                )
            logger.info(f"🔕 Removed push subscription for user {user_id[:10]}...")
            return True
        except Exception as e:
            logger.error(f"Error removing push subscription: {e}")
            return False
    
    async def get_user_subscriptions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all active push subscriptions for a user"""
        try:
            cursor = self.db.push_subscriptions.find({
                "user_id": user_id,
                "active": True
            })
            return await cursor.to_list(length=100)
        except Exception as e:
            logger.error(f"Error fetching push subscriptions: {e}")
            return []
    
    def send_notification(
        self,
        subscription: Dict[str, Any],
        title: str,
        body: str,
        icon: Optional[str] = None,
        url: Optional[str] = None,
        tag: Optional[str] = None
    ) -> bool:
        """Send a push notification to a single subscription"""
        if not self.enabled:
            logger.warning("Push notifications disabled - VAPID keys not configured")
            return False
        
        try:
            payload = json.dumps({
                "title": title,
                "body": body,
                "icon": icon or "/logo192.png",
                "url": url or "/",
                "tag": tag or "moon-hunters-alert",
                "requireInteraction": True
            })
            
            webpush(
                subscription_info={
                    "endpoint": subscription.get("endpoint"),
                    "keys": subscription.get("keys")
                },
                data=payload,
                vapid_private_key=self.vapid_private_key,
                vapid_claims={
                    "sub": self.vapid_email
                }
            )
            logger.info(f"📤 Push notification sent: {title}")
            return True
        except WebPushException as e:
            if e.response and e.response.status_code in [404, 410]:
                logger.info(f"Subscription expired, marking inactive")
            else:
                logger.error(f"Push notification error: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending push notification: {e}")
            return False
    
    async def send_to_user(
        self,
        user_id: str,
        title: str,
        body: str,
        icon: Optional[str] = None,
        url: Optional[str] = None,
        tag: Optional[str] = None
    ) -> int:
        """Send push notification to all of a user's subscriptions"""
        subscriptions = await self.get_user_subscriptions(user_id)
        successful = 0
        
        for sub in subscriptions:
            if self.send_notification(sub, title, body, icon, url, tag):
                successful += 1
            else:
                await self.db.push_subscriptions.update_one(
                    {"_id": sub["_id"]},
                    {"$set": {"active": False}}
                )
        
        return successful
    
    async def send_price_alert(
        self,
        user_id: str,
        symbol: str,
        current_price: float,
        change_percent: float,
        is_pump: bool
    ) -> int:
        """Send price movement alert notification"""
        direction = "🚀 Pump" if is_pump else "📉 Drop"
        title = f"{direction}: {symbol}"
        body = f"{symbol} moved {'+' if change_percent > 0 else ''}{change_percent:.2f}%\nPrice: ${current_price:,.2f}"
        
        return await self.send_to_user(
            user_id,
            title,
            body,
            url=f"/dashboard?coin={symbol}",
            tag=f"price-alert-{symbol}"
        )


push_notification_service: Optional[PushNotificationService] = None


def init_push_notification_service(db) -> PushNotificationService:
    global push_notification_service
    push_notification_service = PushNotificationService(db)
    return push_notification_service


def get_push_notification_service() -> Optional[PushNotificationService]:
    return push_notification_service
