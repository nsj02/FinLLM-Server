# routes/technical.py - 기술적 지표 분석 라우터
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session as SQLSession
from sqlalchemy import func, and_
from typing import List, Dict, Any
from datetime import datetime

from models import get_db, Stock, DailyPrice, TechnicalIndicator
from utils.helpers import get_stock_by_symbol, parse_date, common_responses

router = APIRouter()

@router.get("/technical/rsi", summary="RSI 기준 종목 필터링")
def get_stocks_by_rsi(
    date: str = Query(..., description="조회 날짜 (YYYY-MM-DD)", examples=["2025-01-20"]),
    market: str = Query("ALL", description="시장 (KOSPI/KOSDAQ/ALL)", examples=["KOSPI"]),
    rsi_min: float = Query(0, description="RSI 최소값", examples=[70]),
    rsi_max: float = Query(100, description="RSI 최대값", examples=[100]),
    limit: int = Query(50, description="조회 개수", examples=[20]),
    db: SQLSession = Depends(get_db)
):
    """특정 날짜에 RSI 조건을 만족하는 종목을 조회합니다."""
    try:
        query_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        query = db.query(TechnicalIndicator, Stock).join(
            Stock, TechnicalIndicator.stock_id == Stock.stock_id
        ).filter(
            TechnicalIndicator.date == query_date,
            TechnicalIndicator.rsi.between(rsi_min, rsi_max),
            Stock.is_active == True
        )
        
        if market != "ALL":
            query = query.filter(Stock.market == market)
        
        results = query.limit(limit).all()
        
        stocks = []
        for indicator, stock in results:
            stocks.append({
                "symbol": stock.symbol,
                "name": stock.name,
                "market": stock.market,
                "rsi": indicator.rsi,
                "date": date
            })
        
        return stocks
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/technical/volume-surge", summary="거래량 급증 종목 조회")
def get_volume_surge_stocks(
    date: str = Query(..., description="조회 날짜 (YYYY-MM-DD)", examples=["2024-08-02"]),
    market: str = Query("ALL", description="시장 (KOSPI/KOSDAQ/ALL)", examples=["KOSPI"]),
    volume_ratio_min: float = Query(200, description="거래량 비율 최소값 (%)", examples=[500]),
    limit: int = Query(50, description="조회 개수", examples=[20]),
    db: SQLSession = Depends(get_db)
):
    """특정 날짜에 거래량이 급증한 종목을 조회합니다."""
    try:
        query_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        query = db.query(TechnicalIndicator, Stock).join(
            Stock, TechnicalIndicator.stock_id == Stock.stock_id
        ).filter(
            TechnicalIndicator.date == query_date,
            TechnicalIndicator.volume_ratio >= volume_ratio_min,
            Stock.is_active == True
        )
        
        if market != "ALL":
            query = query.filter(Stock.market == market)
        
        results = query.order_by(TechnicalIndicator.volume_ratio.desc()).limit(limit).all()
        
        stocks = []
        for indicator, stock in results:
            stocks.append({
                "symbol": stock.symbol,
                "name": stock.name,
                "market": stock.market,
                "volume_ratio": indicator.volume_ratio,
                "date": date
            })
        
        return stocks
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/technical/bollinger-touch", summary="볼린저 밴드 터치 종목 조회")
def get_bollinger_touch_stocks(
    date: str = Query(..., description="조회 날짜 (YYYY-MM-DD)", examples=["2025-03-05"]),
    market: str = Query("ALL", description="시장 (KOSPI/KOSDAQ/ALL)", examples=["KOSPI"]),
    band_type: str = Query("lower", description="밴드 유형 (upper/lower)", examples=["lower"]),
    limit: int = Query(50, description="조회 개수", examples=[20]),
    db: SQLSession = Depends(get_db)
):
    """특정 날짜에 볼린저 밴드에 터치한 종목을 조회합니다."""
    try:
        query_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        query = db.query(TechnicalIndicator, Stock).join(
            Stock, TechnicalIndicator.stock_id == Stock.stock_id
        ).filter(
            TechnicalIndicator.date == query_date,
            Stock.is_active == True
        )
        
        if band_type == "upper":
            query = query.filter(TechnicalIndicator.bb_upper_touch == True)
        else:
            query = query.filter(TechnicalIndicator.bb_lower_touch == True)
        
        if market != "ALL":
            query = query.filter(Stock.market == market)
        
        results = query.limit(limit).all()
        
        stocks = []
        for indicator, stock in results:
            stocks.append({
                "symbol": stock.symbol,
                "name": stock.name,
                "market": stock.market,
                "band_type": band_type,
                "date": date
            })
        
        return stocks
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/technical/cross-signals", summary="골든크로스/데드크로스 발생 종목 조회")
def get_cross_signals(
    start_date: str = Query(..., description="시작 날짜 (YYYY-MM-DD)", examples=["2024-09-11"]),
    end_date: str = Query(..., description="끝 날짜 (YYYY-MM-DD)", examples=["2024-10-11"]),
    market: str = Query("ALL", description="시장 (KOSPI/KOSDAQ/ALL)", examples=["KOSPI"]),
    signal_type: str = Query("death_cross", description="시그널 유형 (golden_cross/death_cross)", examples=["death_cross"]),
    limit: int = Query(50, description="조회 개수", examples=[20]),
    db: SQLSession = Depends(get_db)
):
    """특정 기간에 골든크로스/데드크로스가 발생한 종목을 조회합니다."""
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        query = db.query(TechnicalIndicator, Stock).join(
            Stock, TechnicalIndicator.stock_id == Stock.stock_id
        ).filter(
            TechnicalIndicator.date.between(start_dt, end_dt),
            Stock.is_active == True
        )
        
        if signal_type == "golden_cross":
            query = query.filter(TechnicalIndicator.golden_cross == True)
        else:
            query = query.filter(TechnicalIndicator.death_cross == True)
        
        if market != "ALL":
            query = query.filter(Stock.market == market)
        
        results = query.limit(limit).all()
        
        stocks = []
        for indicator, stock in results:
            stocks.append({
                "symbol": stock.symbol,
                "name": stock.name,
                "market": stock.market,
                "signal_type": signal_type,
                "date": indicator.date.isoformat()
            })
        
        return stocks
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/technical/ma-comparison", summary="이동평균 대비 종목 조회")
def get_stocks_above_ma(
    date: str = Query(..., description="조회 날짜 (YYYY-MM-DD)", examples=["2025-03-10"]),
    market: str = Query("ALL", description="시장 (KOSPI/KOSDAQ/ALL)", examples=["KOSPI"]),
    ma_type: str = Query("ma20", description="이동평균 유형 (ma5/ma10/ma20/ma60)", examples=["ma20"]),
    percentage_min: float = Query(0, description="이동평균 대비 최소 상승률 (%)", examples=[10]),
    limit: int = Query(50, description="조회 개수", examples=[20]),
    db: SQLSession = Depends(get_db)
):
    """특정 날짜에 이동평균 대비 일정 비율 이상 상승한 종목을 조회합니다."""
    try:
        query_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        query = db.query(TechnicalIndicator, Stock, DailyPrice).join(
            Stock, TechnicalIndicator.stock_id == Stock.stock_id
        ).join(
            DailyPrice, and_(
                DailyPrice.stock_id == Stock.stock_id,
                DailyPrice.date == TechnicalIndicator.date
            )
        ).filter(
            TechnicalIndicator.date == query_date,
            Stock.is_active == True
        )
        
        if market != "ALL":
            query = query.filter(Stock.market == market)
        
        results = query.all()
        
        stocks = []
        for indicator, stock, price in results:
            # 이동평균 값 선택
            ma_value = getattr(indicator, ma_type, None)
            if ma_value and ma_value > 0:
                percentage = ((price.close_price - ma_value) / ma_value) * 100
                if percentage >= percentage_min:
                    stocks.append({
                        "symbol": stock.symbol,
                        "name": stock.name,
                        "market": stock.market,
                        "close_price": price.close_price,
                        "ma_value": ma_value,
                        "percentage": round(percentage, 2),
                        "ma_type": ma_type,
                        "date": date
                    })
        
        # 상승률 기준 정렬
        stocks.sort(key=lambda x: x["percentage"], reverse=True)
        
        return stocks[:limit]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/technical/cross-count", summary="특정 종목의 골든크로스/데드크로스 발생 횟수")
def get_cross_count_for_stock(
    symbol: str = Query(..., description="종목 심볼", examples=["005930.KS"]),
    start_date: str = Query(..., description="시작 날짜 (YYYY-MM-DD)", examples=["2024-06-01"]),
    end_date: str = Query(..., description="끝 날짜 (YYYY-MM-DD)", examples=["2025-06-30"]),
    db: SQLSession = Depends(get_db)
):
    """특정 종목의 골든크로스/데드크로스 발생 횟수를 조회합니다."""
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        stock = get_stock_by_symbol(db, symbol)
        
        # 골든크로스 횟수
        golden_cross_count = db.query(func.count(TechnicalIndicator.date)).filter(
            TechnicalIndicator.stock_id == stock.stock_id,
            TechnicalIndicator.date.between(start_dt, end_dt),
            TechnicalIndicator.golden_cross == True
        ).scalar()
        
        # 데드크로스 횟수
        death_cross_count = db.query(func.count(TechnicalIndicator.date)).filter(
            TechnicalIndicator.stock_id == stock.stock_id,
            TechnicalIndicator.date.between(start_dt, end_dt),
            TechnicalIndicator.death_cross == True
        ).scalar()
        
        return {
            "symbol": symbol,
            "name": stock.name,
            "start_date": start_date,
            "end_date": end_date,
            "golden_cross_count": golden_cross_count,
            "death_cross_count": death_cross_count,
            "total_cross_count": golden_cross_count + death_cross_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))