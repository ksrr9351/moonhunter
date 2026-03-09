from fastapi import APIRouter, Request, Depends, HTTPException, Query
from typing import Optional
from datetime import datetime, timezone
import logging

from core.deps import db, get_current_user, limiter
from core.schemas import (
    Portfolio, PortfolioCreate, PortfolioAsset,
    Transaction, TransactionCreate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# ==================== PORTFOLIO ENDPOINTS ====================

@router.post("/portfolios")
@limiter.limit("30/minute")
async def create_portfolio(
    request: Request,
    portfolio_data: PortfolioCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new portfolio for the authenticated user"""
    try:
        portfolio = Portfolio(
            user_id=current_user["id"],
            name=portfolio_data.name,
            description=portfolio_data.description
        )
        
        portfolio_dict = portfolio.model_dump()
        portfolio_dict['created_at'] = portfolio_dict['created_at'].isoformat()
        portfolio_dict['updated_at'] = portfolio_dict['updated_at'].isoformat()
        
        await db.portfolios.insert_one(portfolio_dict)
        return portfolio
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating portfolio: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create portfolio")


@router.get("/portfolios")
@limiter.limit("60/minute")
async def get_user_portfolios(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user)
):
    """Get all portfolios for the authenticated user"""
    try:
        query = {"user_id": current_user["id"]}
        
        total = await db.portfolios.count_documents(query)
        
        portfolios = await db.portfolios.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(None)
        
        for portfolio in portfolios:
            if isinstance(portfolio.get('created_at'), str):
                portfolio['created_at'] = datetime.fromisoformat(portfolio['created_at'])
            if isinstance(portfolio.get('updated_at'), str):
                portfolio['updated_at'] = datetime.fromisoformat(portfolio['updated_at'])
        
        return {"portfolios": portfolios, "total": total, "skip": skip, "limit": limit}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching portfolios: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch portfolios")


@router.get("/portfolios/{portfolio_id}")
@limiter.limit("60/minute")
async def get_portfolio(
    request: Request,
    portfolio_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific portfolio"""
    try:
        portfolio = await db.portfolios.find_one(
            {"id": portfolio_id, "user_id": current_user["id"]},
            {"_id": 0}
        )
        
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        
        if isinstance(portfolio.get('created_at'), str):
            portfolio['created_at'] = datetime.fromisoformat(portfolio['created_at'])
        if isinstance(portfolio.get('updated_at'), str):
            portfolio['updated_at'] = datetime.fromisoformat(portfolio['updated_at'])
        
        return portfolio
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching portfolio {portfolio_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch portfolio")


@router.post("/portfolios/{portfolio_id}/assets")
@limiter.limit("30/minute")
async def add_portfolio_asset(
    request: Request,
    portfolio_id: str,
    asset: PortfolioAsset,
    current_user: dict = Depends(get_current_user)
):
    """Add an asset to a portfolio"""
    try:
        portfolio = await db.portfolios.find_one(
            {"id": portfolio_id, "user_id": current_user["id"]},
            {"_id": 0}
        )
        
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        
        asset_dict = asset.model_dump()
        asset_dict['purchase_date'] = asset_dict['purchase_date'].isoformat()
        
        portfolio['assets'].append(asset_dict)
        portfolio['total_investment'] = portfolio.get('total_investment', 0) + (asset.amount * asset.purchase_price)
        portfolio['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        await db.portfolios.update_one(
            {"id": portfolio_id},
            {"$set": {
                "assets": portfolio['assets'],
                "total_investment": portfolio['total_investment'],
                "updated_at": portfolio['updated_at']
            }}
        )
        
        return {"message": "Asset added successfully", "portfolio": portfolio}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding asset to portfolio {portfolio_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to add asset to portfolio")


# ==================== TRANSACTION ENDPOINTS ====================

@router.post("/transactions")
@limiter.limit("30/minute")
async def create_transaction(
    request: Request,
    transaction_data: TransactionCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new transaction"""
    try:
        total = transaction_data.amount * transaction_data.price
        
        transaction = Transaction(
            user_id=current_user["id"],
            portfolio_id=transaction_data.portfolio_id,
            transaction_type=transaction_data.transaction_type,
            symbol=transaction_data.symbol,
            amount=transaction_data.amount,
            price=transaction_data.price,
            total=total
        )
        
        transaction_dict = transaction.model_dump()
        transaction_dict['timestamp'] = transaction_dict['timestamp'].isoformat()
        
        await db.transactions.insert_one(transaction_dict)
        return transaction
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating transaction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create transaction")


@router.get("/transactions")
@limiter.limit("60/minute")
async def get_user_transactions(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user)
):
    """Get transaction history for the authenticated user"""
    try:
        query = {"user_id": current_user["id"]}
        
        total = await db.transactions.count_documents(query)
        
        transactions = await db.transactions.find(
            query,
            {"_id": 0}
        ).sort("timestamp", -1).skip(skip).limit(limit).to_list(None)
        
        for transaction in transactions:
            if isinstance(transaction.get('timestamp'), str):
                transaction['timestamp'] = datetime.fromisoformat(transaction['timestamp'])
        
        return {"transactions": transactions, "total": total, "skip": skip, "limit": limit}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch transactions")


@router.delete("/transactions/clear")
@limiter.limit("5/minute")
async def clear_user_transactions(request: Request, current_user: dict = Depends(get_current_user)):
    """Clear all transaction history for the authenticated user"""
    try:
        result = await db.transactions.delete_many({"user_id": current_user["id"]})
        return {
            "message": "Transaction history cleared successfully",
            "deleted_count": result.deleted_count
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing transactions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to clear transactions")
