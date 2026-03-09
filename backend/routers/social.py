from fastapi import APIRouter, Depends, HTTPException, Query, Request
import logging

from core.deps import db, get_current_user, social_trading, limiter
from core.schemas import SocialSettingsUpdate, CopySettingsUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.get("/social/leaderboard")
@limiter.limit("30/minute")
async def get_leaderboard(
    request: Request,
    period: str = Query("all", regex="^(week|month|all)$"),
    limit: int = Query(20, ge=1, le=50)
):
    """Get the trading leaderboard"""
    try:
        leaderboard = await social_trading.get_leaderboard(period=period, limit=limit)
        return {"leaderboard": leaderboard, "period": period}
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/social/trader/{trader_id}")
@limiter.limit("30/minute")
async def get_trader_public_portfolio(request: Request, trader_id: str):
    """Get a trader's public portfolio"""
    try:
        portfolio = await social_trading.get_public_portfolio(trader_id)
        if "error" in portfolio:
            raise HTTPException(status_code=403, detail=portfolio["error"])
        followers = await social_trading.get_followers(trader_id)
        portfolio["followers"] = followers
        return portfolio
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching trader portfolio: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/social/settings")
@limiter.limit("20/minute")
async def get_social_settings(request: Request, current_user: dict = Depends(get_current_user)):
    """Get current user's social trading settings"""
    try:
        user_id = current_user.get("wallet_address") or str(current_user["_id"])
        settings = await social_trading.get_social_settings(user_id)
        return settings
    except Exception as e:
        logger.error(f"Error fetching social settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/social/settings")
@limiter.limit("20/minute")
async def update_social_settings(
    request: Request,
    settings: SocialSettingsUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update current user's social trading settings"""
    try:
        user_id = current_user.get("wallet_address") or str(current_user["_id"])
        updated = await social_trading.update_social_settings(
            user_id,
            public_portfolio=settings.public_portfolio,
            allow_copy=settings.allow_copy,
            display_name=settings.display_name
        )
        return updated
    except Exception as e:
        logger.error(f"Error updating social settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/social/following")
@limiter.limit("20/minute")
async def get_following(request: Request, current_user: dict = Depends(get_current_user)):
    """Get list of traders the current user is following"""
    try:
        user_id = current_user.get("wallet_address") or str(current_user["_id"])
        following = await social_trading.get_following(user_id)
        return {"following": following}
    except Exception as e:
        logger.error(f"Error fetching following: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/social/follow/{trader_id}")
@limiter.limit("20/minute")
async def follow_trader(request: Request, trader_id: str, current_user: dict = Depends(get_current_user)):
    """Follow a trader"""
    try:
        user_id = current_user.get("wallet_address") or str(current_user["_id"])
        result = await social_trading.follow_trader(user_id, trader_id)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error following trader: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/social/follow/{trader_id}")
@limiter.limit("20/minute")
async def unfollow_trader(request: Request, trader_id: str, current_user: dict = Depends(get_current_user)):
    """Unfollow a trader"""
    try:
        user_id = current_user.get("wallet_address") or str(current_user["_id"])
        success = await social_trading.unfollow_trader(user_id, trader_id)
        return {"success": success}
    except Exception as e:
        logger.error(f"Error unfollowing trader: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/social/copy-settings/{trader_id}")
@limiter.limit("20/minute")
async def update_copy_settings(
    request: Request,
    trader_id: str,
    settings: CopySettingsUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update copy trading settings for a followed trader"""
    try:
        user_id = current_user.get("wallet_address") or str(current_user["_id"])
        success = await social_trading.update_copy_settings(
            user_id,
            trader_id,
            copy_enabled=settings.copy_enabled,
            copy_percentage=settings.copy_percentage,
            max_per_trade=settings.max_per_trade
        )
        return {"success": success}
    except Exception as e:
        logger.error(f"Error updating copy settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/social/activity")
@limiter.limit("20/minute")
async def get_activity_feed(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Get activity feed from followed traders"""
    try:
        user_id = current_user.get("wallet_address") or str(current_user["_id"])
        activity = await social_trading.get_activity_feed(user_id, limit=limit)
        return {"activity": activity}
    except Exception as e:
        logger.error(f"Error fetching activity feed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/social/my-stats")
@limiter.limit("20/minute")
async def get_my_stats(request: Request, current_user: dict = Depends(get_current_user)):
    """Get current user's trading statistics"""
    try:
        user_id = current_user.get("wallet_address") or str(current_user["_id"])
        stats = await social_trading.get_trader_stats(user_id)
        followers = await social_trading.get_followers(user_id)
        return {"stats": stats, "followers": followers}
    except Exception as e:
        logger.error(f"Error fetching user stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
