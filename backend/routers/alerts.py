from fastapi import APIRouter, Request, Depends, HTTPException
import os
from datetime import datetime, timezone
import logging

from core.deps import db, get_current_user, push_service, limiter
from core.schemas import AlertSettings, PushSubscription, PushUnsubscribe

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# ==================== ALERT SETTINGS ====================

@router.get("/alert-settings")
@limiter.limit("60/minute")
async def get_alert_settings(request: Request, current_user: dict = Depends(get_current_user)):
    """Get user's alert settings"""
    try:
        user_id = current_user.get("id")
        settings = await db.alert_settings.find_one({"user_id": user_id}, {"_id": 0})
        
        if not settings:
            return {
                "email_alerts": False,
                "threshold": 5,
                "email": current_user.get("email", ""),
                "last_alert": None
            }
        
        return settings
        
    except Exception as e:
        logger.error(f"Error fetching alert settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch settings")


@router.post("/alert-settings")
@limiter.limit("30/minute")
async def update_alert_settings(
    request: Request,
    settings: AlertSettings,
    current_user: dict = Depends(get_current_user)
):
    """Update user's alert settings"""
    try:
        user_id = current_user.get("id")
        settings_dict = settings.model_dump()
        settings_dict["user_id"] = user_id
        settings_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        await db.alert_settings.update_one(
            {"user_id": user_id},
            {"$set": settings_dict},
            upsert=True
        )
        
        logger.info(f"Updated alert settings for user {user_id}")
        return settings_dict
        
    except Exception as e:
        logger.error(f"Error updating alert settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update settings")


# ==================== PUSH NOTIFICATIONS ====================

@router.get("/push/vapid-key")
@limiter.limit("30/minute")
async def get_vapid_public_key(request: Request):
    """Get VAPID public key for push notification subscription"""
    vapid_key = os.environ.get('VAPID_PUBLIC_KEY', '')
    return {"vapid_public_key": vapid_key}


@router.post("/push/subscribe")
@limiter.limit("30/minute")
async def subscribe_push(
    request: Request,
    subscription: PushSubscription,
    current_user: dict = Depends(get_current_user)
):
    """Subscribe to push notifications"""
    try:
        user_id = current_user.get("id")
        
        success = await push_service.save_subscription(
            user_id,
            subscription.model_dump()
        )
        
        if success:
            await db.alert_settings.update_one(
                {"user_id": user_id},
                {"$set": {"push_enabled": True}},
                upsert=True
            )
            return {"success": True, "message": "Push notifications enabled"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save subscription")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error subscribing to push: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to subscribe")


@router.post("/push/unsubscribe")
@limiter.limit("30/minute")
async def unsubscribe_push(
    request: Request,
    data: PushUnsubscribe,
    current_user: dict = Depends(get_current_user)
):
    """Unsubscribe from push notifications"""
    try:
        user_id = current_user.get("id")
        
        success = await push_service.remove_subscription(
            user_id,
            data.endpoint
        )
        
        if success:
            remaining = await push_service.get_user_subscriptions(user_id)
            if not remaining:
                await db.alert_settings.update_one(
                    {"user_id": user_id},
                    {"$set": {"push_enabled": False}}
                )
            return {"success": True, "message": "Push notifications disabled"}
        else:
            raise HTTPException(status_code=500, detail="Failed to remove subscription")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unsubscribing from push: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to unsubscribe")


@router.post("/push/test")
@limiter.limit("5/minute")
async def test_push_notification(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Send a test push notification"""
    try:
        user_id = current_user.get("id")
        
        sent = await push_service.send_to_user(
            user_id,
            "Test Notification",
            "Push notifications are working! You'll receive price alerts here.",
            url="/dashboard"
        )
        
        if sent > 0:
            return {"success": True, "message": f"Test notification sent to {sent} device(s)"}
        else:
            return {"success": False, "message": "No active push subscriptions found"}
            
    except Exception as e:
        logger.error(f"Error sending test push: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to send test notification")
