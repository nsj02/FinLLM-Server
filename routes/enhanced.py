# routes/enhanced.py - 고급 API 라우터
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session as SQLSession
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy import desc, asc

from models import get_db, Stock, DailyPrice, MarketIndex, MarketStat
from utils.helpers import get_stock_by_symbol, parse_date, common_responses

router = APIRouter()

@router.get("/stock/price", summary="특정 날짜 주식 가격 조회")
def get_stock_price_by_date(
    ticker: str = Query(..., description="주식 티커", examples=["005930.KS"]),
    date: str = Query(..., description="조회 날짜 (YYYY-MM-DD)", examples=["2024-01-01"]),
    price_type: str = Query("close", description="가격 유형 (open/high/low/close/volume)", examples=["close"]),
    db: SQLSession = Depends(get_db)
):
    """특정 날짜의 주식 가격 정보를 조회합니다."""
    try:
        query_date = parse_date(date).date()
        
        stock = get_stock_by_symbol(db, ticker)
        
        price_data = db.query(DailyPrice).filter(
            DailyPrice.stock_id == stock.stock_id,
            DailyPrice.date == query_date
        ).first()
        
        if not price_data:
            raise HTTPException(status_code=404, detail=f"No price data found for {ticker} on {date}")
        
        result = {
            "symbol": ticker,
            "name": stock.name,
            "date": date,
            "open": price_data.open_price,
            "high": price_data.high_price,
            "low": price_data.low_price,
            "close": price_data.close_price,
            "volume": price_data.volume,
            "change": price_data.change,
            "change_rate": price_data.change_rate
        }
        
        if price_type in ["open", "high", "low", "close", "volume"]:
            price_map = {
                "open": price_data.open_price,
                "high": price_data.high_price,
                "low": price_data.low_price,
                "close": price_data.close_price,
                "volume": price_data.volume
            }
            result["requested_value"] = price_map[price_type]
        
        return result
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market/stats", summary="시장 통계 조회")
def get_market_stats_by_date(
    date: str = Query(..., description="조회 날짜 (YYYY-MM-DD)", examples=["2024-01-01"]),
    market: str = Query("ALL", description="시장 (KOSPI/KOSDAQ/ALL)", examples=["KOSPI"]),
    db: SQLSession = Depends(get_db)
):
    """특정 날짜의 시장 통계를 조회합니다."""
    try:
        query_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        market_stat = db.query(MarketStat).filter(
            MarketStat.date == query_date,
            MarketStat.market == market
        ).first()
        
        if not market_stat:
            raise HTTPException(status_code=404, detail=f"No market stats found for {market} on {date}")
        
        return {
            "date": date,
            "market": market,
            "rising_stocks": market_stat.rising_stocks,
            "falling_stocks": market_stat.falling_stocks,
            "unchanged_stocks": market_stat.unchanged_stocks,
            "total_stocks": market_stat.total_stocks,
            "total_volume": market_stat.total_volume,
            "total_value": market_stat.total_value
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market/index", summary="시장 지수 조회")
def get_market_index_by_date(
    date: str = Query(..., description="조회 날짜 (YYYY-MM-DD)", examples=["2024-01-01"]),
    market: str = Query("KOSPI", description="시장 (KOSPI/KOSDAQ)", examples=["KOSPI"]),
    db: SQLSession = Depends(get_db)
):
    """특정 날짜의 시장 지수를 조회합니다."""
    try:
        query_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        market_index = db.query(MarketIndex).filter(
            MarketIndex.date == query_date,
            MarketIndex.market == market
        ).first()
        
        if not market_index:
            raise HTTPException(status_code=404, detail=f"No market index found for {market} on {date}")
        
        return {
            "date": date,
            "market": market,
            "open": market_index.open_index,
            "high": market_index.high_index,
            "low": market_index.low_index,
            "close": market_index.close_index,
            "volume": market_index.volume,
            "change": market_index.change,
            "change_rate": market_index.change_rate
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market/rankings", summary="시장 순위 조회")
def get_market_rankings(
    date: str = Query(..., description="조회 날짜 (YYYY-MM-DD)", examples=["2024-01-01"]),
    market: str = Query("KOSPI", description="시장 (KOSPI/KOSDAQ)", examples=["KOSPI"]),
    sort_by: str = Query("change_rate", description="정렬 기준 (change_rate/volume/close_price)", examples=["change_rate"]),
    order: str = Query("desc", description="정렬 순서 (desc/asc)", examples=["desc"]),
    limit: int = Query(10, description="조회 개수", examples=[10]),
    db: SQLSession = Depends(get_db)
):
    """특정 날짜의 시장 순위를 조회합니다."""
    try:
        from sqlalchemy import desc, asc
        
        query_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        # 기본 쿼리
        query = db.query(DailyPrice, Stock).join(Stock, DailyPrice.stock_id == Stock.stock_id).filter(
            DailyPrice.date == query_date,
            Stock.market == market,
            Stock.is_active == True
        )
        
        # 정렬 기준 설정
        sort_columns = {
            "change_rate": DailyPrice.change_rate,
            "volume": DailyPrice.volume,
            "close_price": DailyPrice.close_price
        }
        sort_column = sort_columns.get(sort_by, DailyPrice.change_rate)
        
        # 정렬 순서 설정
        if order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
        
        results = query.limit(limit).all()
        
        if not results:
            raise HTTPException(status_code=404, detail=f"No data found for {market} on {date}")
        
        rankings = []
        for i, (price, stock) in enumerate(results, 1):
            rankings.append({
                "rank": i,
                "symbol": stock.symbol,
                "name": stock.name,
                "market": stock.market,
                "open": price.open_price,
                "high": price.high_price,
                "low": price.low_price,
                "close": price.close_price,
                "volume": price.volume,
                "change": price.change,
                "change_rate": price.change_rate
            })
        
        return rankings
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stocks/search", summary="종목 검색")
def search_stocks(
    query: str = Query(..., description="검색어 (종목명 또는 코드)", examples=["삼성"]),
    market: str = Query("ALL", description="시장 (KOSPI/KOSDAQ/ALL)", examples=["ALL"]),
    limit: int = Query(10, description="조회 개수", examples=[10]),
    db: SQLSession = Depends(get_db)
):
    """종목명 또는 코드로 종목을 검색합니다."""
    try:
        base_query = db.query(Stock).filter(Stock.is_active == True)
        
        if market != "ALL":
            base_query = base_query.filter(Stock.market == market)
        
        # 종목명 또는 심볼로 검색
        search_query = base_query.filter(
            (Stock.name.contains(query)) | 
            (Stock.symbol.contains(query)) |
            (Stock.krx_code.contains(query))
        ).limit(limit)
        
        results = search_query.all()
        
        stocks = []
        for stock in results:
            stocks.append({
                "symbol": stock.symbol,
                "krx_code": stock.krx_code,
                "name": stock.name,
                "market": stock.market,
                "sector": stock.sector,
                "industry": stock.industry
            })
        
        return stocks
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))