# utils/helpers.py - 공통 헬퍼 함수들

from functools import lru_cache
from fastapi import HTTPException
from sqlalchemy.orm import Session as SQLSession
from typing import Dict, Any, Optional
from datetime import datetime

from models import Stock


@lru_cache(maxsize=1000)
def get_stock_by_symbol_cached(symbol: str, db_session_id: str) -> Optional[Stock]:
    """Cached version of stock lookup (for frequently accessed stocks)."""
    # Note: This is a simplified cache - in production, use Redis or similar
    return None


def get_stock_by_symbol(db: SQLSession, symbol: str) -> Stock:
    """Helper function to get a Stock object from database with optimized query."""
    # Use only() to limit columns loaded for better performance
    stock = db.query(Stock).filter(
        Stock.symbol == symbol.upper(), 
        Stock.is_active == True
    ).first()
    
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock '{symbol}' not found in database.")
    return stock


def parse_date(date_str: str) -> datetime:
    """Helper function to parse date string to datetime object."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {date_str}. Expected YYYY-MM-DD.")


def validate_limit(limit: int, max_limit: int = 100) -> int:
    """Validate and constrain limit parameter."""
    if limit <= 0:
        raise HTTPException(status_code=400, detail="Limit must be positive")
    if limit > max_limit:
        raise HTTPException(status_code=400, detail=f"Limit cannot exceed {max_limit}")
    return limit


def build_stock_response(stock: Stock, price_data=None, additional_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Helper function to build standardized stock response."""
    response = {
        "symbol": stock.symbol,
        "name": stock.name,
        "market": stock.market,
        "sector": stock.sector,
        "industry": stock.industry
    }
    
    if price_data:
        response.update({
            "close_price": price_data.close_price,
            "open_price": price_data.open_price,
            "high_price": price_data.high_price,
            "low_price": price_data.low_price,
            "volume": price_data.volume,
            "change": price_data.change,
            "change_rate": price_data.change_rate,
            "date": price_data.date.isoformat()
        })
    
    if additional_data:
        response.update(additional_data)
    
    return response


def handle_database_error(e: Exception) -> HTTPException:
    """Centralized database error handling."""
    if "connection" in str(e).lower():
        return HTTPException(status_code=503, detail="Database connection error")
    return HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# 공통 응답 스키마
common_responses = {
    400: {"description": "Bad Request"},
    404: {"description": "Not Found"},
    500: {"description": "Internal Server Error"},
    503: {"description": "Service Unavailable"},
}

# 공통 상수
DEFAULT_LIMIT = 50
MAX_LIMIT = 100