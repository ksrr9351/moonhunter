from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from typing import List
import logging
import asyncio
import json
from datetime import datetime, timezone

from core.deps import db, get_current_user, event_service, limiter
from core.schemas import StatusCheck, StatusCheckCreate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.post("/status", response_model=StatusCheck)
@limiter.limit("60/minute")
async def create_status_check(request: Request, input: StatusCheckCreate, current_user: dict = Depends(get_current_user)):
    try:
        status_dict = input.model_dump()
        status_obj = StatusCheck(**status_dict)
        
        doc = status_obj.model_dump()
        doc['timestamp'] = doc['timestamp'].isoformat()
        
        await db.status_checks.insert_one(doc)
        return status_obj
    except Exception as e:
        logger.error(f"Error creating status check: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/status", response_model=List[StatusCheck])
@limiter.limit("60/minute")
async def get_status_checks(request: Request, current_user: dict = Depends(get_current_user)):
    try:
        status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
        
        for check in status_checks:
            if isinstance(check['timestamp'], str):
                check['timestamp'] = datetime.fromisoformat(check['timestamp'])
        
        return status_checks
    except Exception as e:
        logger.error(f"Error fetching status checks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/events/stream")
async def event_stream(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Server-Sent Events stream for real-time updates.
    Subscribe to receive wallet, swap, AI trade, and auto-invest events.
    """
    user_id = current_user["id"]
    
    async def generate():
        queue = await event_service.subscribe(user_id)
        try:
            connected_data = json.dumps({"user_id": f"{user_id[:8]}...", "status": "connected"})
            yield f"event: connected\ndata: {connected_data}\n\n"
            
            while True:
                if await request.is_disconnected():
                    break
                
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield event.to_sse_format()
                except asyncio.TimeoutError:
                    heartbeat_data = json.dumps({"timestamp": datetime.now(timezone.utc).isoformat()})
                    yield f"event: heartbeat\ndata: {heartbeat_data}\n\n"
                except Exception as e:
                    logger.error(f"SSE stream error: {e}", exc_info=True)
                    break
        finally:
            await event_service.unsubscribe(user_id, queue)
            logger.info(f"SSE stream closed for user {user_id[:8]}...")
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


