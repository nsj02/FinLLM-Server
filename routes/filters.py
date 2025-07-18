# routes/filters.py - 필터링 기능 라우터
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session as SQLSession
from typing import List, Dict, Any
from datetime import datetime, timedelta

from models import get_db, Stock, DailyPrice
from utils.helpers import parse_date, common_responses

router = APIRouter()

@router.get("/filter/volume-change", summary="전날대비 거래량 증가 종목 조회")
def get_volume_change_stocks(
    date: str = Query(..., description="조회 날짜 (YYYY-MM-DD)", examples=["2025-05-14"]),
    market: str = Query("ALL", description="시장 (KOSPI/KOSDAQ/ALL)", examples=["ALL"]),
    volume_change_min: float = Query(200, description="전날대비 거래량 증가율 최소값 (%)", examples=[300]),
    limit: int = Query(50, description="조회 개수", examples=[20]),
    db: SQLSession = Depends(get_db)
):
    """전날대비 거래량이 일정 비율 이상 증가한 종목을 조회합니다."""
    try:
        query_date = parse_date(date).date()
        prev_date = query_date - timedelta(days=1)
        
        # 현재 날짜와 전날 데이터 조인
        current_query = db.query(DailyPrice, Stock).join(
            Stock, DailyPrice.stock_id == Stock.stock_id
        ).filter(
            DailyPrice.date == query_date,
            Stock.is_active == True
        )
        
        if market != "ALL":
            current_query = current_query.filter(Stock.market == market)
        
        results = []
        for current_price, stock in current_query.all():
            # 전날 데이터 조회
            prev_price = db.query(DailyPrice).filter(
                DailyPrice.stock_id == stock.stock_id,
                DailyPrice.date == prev_date
            ).first()
            
            if prev_price and prev_price.volume > 0:
                volume_change = ((current_price.volume - prev_price.volume) / prev_price.volume) * 100
                if volume_change >= volume_change_min:
                    results.append({
                        "symbol": stock.symbol,
                        "name": stock.name,
                        "market": stock.market,
                        "current_volume": current_price.volume,
                        "previous_volume": prev_price.volume,
                        "volume_change_percent": round(volume_change, 2),
                        "date": date
                    })
        
        # 거래량 증가율 기준 정렬
        results.sort(key=lambda x: x["volume_change_percent"], reverse=True)
        
        return results[:limit]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/filter/volume-absolute", summary="절대 거래량 기준 종목 조회")
def get_high_volume_stocks(
    date: str = Query(..., description="조회 날짜 (YYYY-MM-DD)", examples=["2024-11-22"]),
    market: str = Query("ALL", description="시장 (KOSPI/KOSDAQ/ALL)", examples=["ALL"]),
    volume_min: int = Query(1000000, description="최소 거래량 (주)", examples=[20000000]),
    limit: int = Query(50, description="조회 개수", examples=[20]),
    db: SQLSession = Depends(get_db)
):
    """절대 거래량이 일정 수준 이상인 종목을 조회합니다."""
    try:
        query_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        query = db.query(DailyPrice, Stock).join(
            Stock, DailyPrice.stock_id == Stock.stock_id
        ).filter(
            DailyPrice.date == query_date,
            DailyPrice.volume >= volume_min,
            Stock.is_active == True
        )
        
        if market != "ALL":
            query = query.filter(Stock.market == market)
        
        results = query.order_by(DailyPrice.volume.desc()).limit(limit).all()
        
        stocks = []
        for price, stock in results:
            stocks.append({
                "symbol": stock.symbol,
                "name": stock.name,
                "market": stock.market,
                "volume": price.volume,
                "close_price": price.close_price,
                "change_rate": price.change_rate,
                "date": date
            })
        
        return stocks
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/filter/price-range", summary="종가 범위 기준 종목 조회")
def get_stocks_by_price_range(
    date: str = Query(..., description="조회 날짜 (YYYY-MM-DD)", examples=["2025-05-16"]),
    market: str = Query("ALL", description="시장 (KOSPI/KOSDAQ/ALL)", examples=["ALL"]),
    price_min: float = Query(0, description="최소 종가", examples=[100000]),
    price_max: float = Query(1000000, description="최대 종가", examples=[200000]),
    limit: int = Query(50, description="조회 개수", examples=[20]),
    db: SQLSession = Depends(get_db)
):
    """종가가 특정 범위에 있는 종목을 조회합니다."""
    try:
        query_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        query = db.query(DailyPrice, Stock).join(
            Stock, DailyPrice.stock_id == Stock.stock_id
        ).filter(
            DailyPrice.date == query_date,
            DailyPrice.close_price.between(price_min, price_max),
            Stock.is_active == True
        )
        
        if market != "ALL":
            query = query.filter(Stock.market == market)
        
        results = query.order_by(DailyPrice.close_price.desc()).limit(limit).all()
        
        stocks = []
        for price, stock in results:
            stocks.append({
                "symbol": stock.symbol,
                "name": stock.name,
                "market": stock.market,
                "close_price": price.close_price,
                "volume": price.volume,
                "change_rate": price.change_rate,
                "date": date
            })
        
        return stocks
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/filter/change-rate", summary="등락률 기준 종목 조회")
def get_stocks_by_change_rate(
    date: str = Query(..., description="조회 날짜 (YYYY-MM-DD)", examples=["2024-09-09"]),
    market: str = Query("ALL", description="시장 (KOSPI/KOSDAQ/ALL)", examples=["ALL"]),
    change_rate_min: float = Query(-100, description="최소 등락률 (%)", examples=[-10]),
    change_rate_max: float = Query(100, description="최대 등락률 (%)", examples=[100]),
    limit: int = Query(50, description="조회 개수", examples=[20]),
    db: SQLSession = Depends(get_db)
):
    """등락률이 특정 범위에 있는 종목을 조회합니다."""
    try:
        query_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        query = db.query(DailyPrice, Stock).join(
            Stock, DailyPrice.stock_id == Stock.stock_id
        ).filter(
            DailyPrice.date == query_date,
            DailyPrice.change_rate.between(change_rate_min, change_rate_max),
            Stock.is_active == True
        )
        
        if market != "ALL":
            query = query.filter(Stock.market == market)
        
        results = query.order_by(DailyPrice.change_rate.desc()).limit(limit).all()
        
        stocks = []
        for price, stock in results:
            stocks.append({
                "symbol": stock.symbol,
                "name": stock.name,
                "market": stock.market,
                "close_price": price.close_price,
                "volume": price.volume,
                "change_rate": price.change_rate,
                "date": date
            })
        
        return stocks
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/filter/combined", summary="복합 조건 종목 조회")
def get_stocks_by_combined_conditions(
    date: str = Query(..., description="조회 날짜 (YYYY-MM-DD)", examples=["2024-08-30"]),
    market: str = Query("ALL", description="시장 (KOSPI/KOSDAQ/ALL)", examples=["ALL"]),
    change_rate_min: float = Query(-100, description="최소 등락률 (%)", examples=[5]),
    change_rate_max: float = Query(100, description="최대 등락률 (%)", examples=[100]),
    volume_change_min: float = Query(0, description="전날대비 거래량 증가율 최소값 (%)", examples=[300]),
    volume_min: int = Query(0, description="최소 거래량 (주)", examples=[0]),
    price_min: float = Query(0, description="최소 종가", examples=[0]),
    price_max: float = Query(1000000, description="최대 종가", examples=[1000000]),
    limit: int = Query(50, description="조회 개수", examples=[20]),
    db: SQLSession = Depends(get_db)
):
    """등락률과 거래량 증가율을 동시에 만족하는 종목을 조회합니다."""
    try:
        query_date = datetime.strptime(date, "%Y-%m-%d").date()
        prev_date = query_date - timedelta(days=1)
        
        # 현재 날짜 데이터 조회
        current_query = db.query(DailyPrice, Stock).join(
            Stock, DailyPrice.stock_id == Stock.stock_id
        ).filter(
            DailyPrice.date == query_date,
            DailyPrice.change_rate.between(change_rate_min, change_rate_max),
            DailyPrice.close_price.between(price_min, price_max),
            DailyPrice.volume >= volume_min,
            Stock.is_active == True
        )
        
        if market != "ALL":
            current_query = current_query.filter(Stock.market == market)
        
        results = []
        for current_price, stock in current_query.all():
            # 전날 데이터 조회
            prev_price = db.query(DailyPrice).filter(
                DailyPrice.stock_id == stock.stock_id,
                DailyPrice.date == prev_date
            ).first()
            
            volume_change = 0
            if prev_price and prev_price.volume > 0:
                volume_change = ((current_price.volume - prev_price.volume) / prev_price.volume) * 100
            
            if volume_change >= volume_change_min:
                results.append({
                    "symbol": stock.symbol,
                    "name": stock.name,
                    "market": stock.market,
                    "close_price": current_price.close_price,
                    "change_rate": current_price.change_rate,
                    "volume": current_price.volume,
                    "volume_change_percent": round(volume_change, 2),
                    "date": date
                })
        
        # 등락률 기준 정렬
        results.sort(key=lambda x: x["change_rate"], reverse=True)
        
        return results[:limit]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))