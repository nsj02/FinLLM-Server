# routes/basic.py - 기본 API 라우터
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session as SQLSession
from typing import List, Dict, Any
from datetime import datetime, timedelta

from models import get_db, Stock, DailyPrice, MarketIndex, MarketStat
from utils.helpers import get_stock_by_symbol, parse_date, common_responses, validate_limit, handle_database_error

router = APIRouter()

# 응답 모델 정의
StockHistoryData = Dict[str, Any]
StockInfoData = Dict[str, Any]
StockActionData = Dict[str, Any]
FinancialsData = Dict[str, Any]
HolderData = Dict[str, Any]
RecommendationData = Dict[str, Any]

@router.get("/", summary="API 상태 확인")
def root():
    return {"message": "Yahoo Finance API Server is running", "version": "2.0.0"}

@router.get("/health", summary="헬스체크")
def health_check():
    return {"status": "healthy", "service": "yahoo-finance-api"}

@router.get("/stock/history", summary="주식 과거 시세 조회", responses=common_responses)
def get_historical_stock_prices(
    ticker: str = Query(..., description="조회할 주식의 티커", examples=["005930.KS"]),
    days: int = Query(30, description="조회할 일수", examples=[365]),
    db: SQLSession = Depends(get_db)
):
    """주식의 과거 시세를 조회합니다."""
    try:
        # 입력 검증
        if days <= 0 or days > 3650:  # 최대 10년
            raise HTTPException(status_code=400, detail="Days must be between 1 and 3650")
        
        stock = get_stock_by_symbol(db, ticker)
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # 최적화된 쿼리 - 필요한 컬럼만 선택
        prices = db.query(DailyPrice).filter(
            DailyPrice.stock_id == stock.stock_id,
            DailyPrice.date >= start_date,
            DailyPrice.date <= end_date
        ).order_by(DailyPrice.date.desc()).all()
        
        # 리스트 컴프리헨션으로 성능 개선
        result = [
            {
                "Date": price.date.isoformat(),
                "Open": price.open_price,
                "High": price.high_price,
                "Low": price.low_price,
                "Close": price.close_price,
                "Adj_Close": price.adjusted_close,
                "Volume": price.volume,
                "Change": price.change,
                "Change_Rate": price.change_rate
            }
            for price in prices
        ]
        
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise handle_database_error(e)

@router.get("/stock/info", summary="주식 종합 정보 조회", responses=common_responses)
def get_stock_info(
    ticker: str = Query(..., description="조회할 주식의 티커", examples=["005930.KS"]), 
    db: SQLSession = Depends(get_db)
):
    """주식의 종합 정보를 조회합니다."""
    try:
        stock = get_stock_by_symbol(db, ticker)
        
        # 최근 가격 정보 가져오기
        latest_price = db.query(DailyPrice).filter(
            DailyPrice.stock_id == stock.stock_id
        ).order_by(DailyPrice.date.desc()).first()
        
        info = {
            "symbol": stock.symbol,
            "longName": stock.name,
            "sector": stock.sector,
            "industry": stock.industry,
            "market": stock.market,
            "currentPrice": latest_price.close_price if latest_price else None,
            "previousClose": latest_price.close_price if latest_price else None,
            "open": latest_price.open_price if latest_price else None,
            "dayHigh": latest_price.high_price if latest_price else None,
            "dayLow": latest_price.low_price if latest_price else None,
            "volume": latest_price.volume if latest_price else None,
            "lastUpdate": latest_price.date.isoformat() if latest_price else None
        }
        
        return info
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stock/actions", summary="주식 활동(배당, 분할) 조회", responses=common_responses)
def get_stock_actions(
    ticker: str = Query(..., description="조회할 주식의 티커", examples=["005930.KS"]), 
    db: SQLSession = Depends(get_db)
):
    """주식의 배당 및 분할 정보를 조회합니다."""
    try:
        stock = get_stock_by_symbol(db, ticker)
        # 현재 구현에서는 배당/분할 데이터가 없으므로 빈 리스트 반환
        return []
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stock/financials", summary="재무제표 조회", responses=common_responses)
def get_financial_statement(
    ticker: str = Query(..., description="조회할 주식의 티커", examples=["005930.KS"]),
    financial_type: str = Query(..., description="조회할 재무제표 종류", examples=["income_stmt"]),
    db: SQLSession = Depends(get_db)
):
    """재무제표를 조회합니다."""
    try:
        stock = get_stock_by_symbol(db, ticker)
        # 현재 구현에서는 재무제표 데이터가 없으므로 빈 리스트 반환
        return []
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stock/holders", summary="주주 정보 조회", responses=common_responses)
def get_holder_info(
    ticker: str = Query(..., description="조회할 주식의 티커", examples=["005930.KS"]),
    holder_type: str = Query(..., description="조회할 주주 정보 종류", examples=["major_holders"]),
    db: SQLSession = Depends(get_db)
):
    """주주 정보를 조회합니다."""
    try:
        stock = get_stock_by_symbol(db, ticker)
        # 현재 구현에서는 주주 정보가 없으므로 빈 리스트 반환
        return []
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stock/recommendations", summary="애널리스트 추천 정보 조회", responses=common_responses)
def get_recommendations(
    ticker: str = Query(..., description="조회할 주식의 티커", examples=["005930.KS"]),
    recommendation_type: str = Query("recommendations", description="조회할 추천 정보 종류", examples=["upgrades_downgrades"]),
    months_back: int = Query(12, description="upgrades_downgrades 조회 시, 과거 몇 개월까지의 데이터를 볼지 설정", ge=1),
    db: SQLSession = Depends(get_db)
):
    """애널리스트 추천 정보를 조회합니다."""
    try:
        stock = get_stock_by_symbol(db, ticker)
        # 현재 구현에서는 추천 정보가 없으므로 빈 리스트 반환
        return []
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))