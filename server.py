# server.py - API 서버 (데이터베이스 분리 버전)

import json
from enum import Enum
from typing import List, Optional, Any, Dict
import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session as SQLSession
from sqlalchemy.sql import func

# ==============================================================================
# 1. Pydantic 응답 모델(Response Models)
# ==============================================================================

class Message(BaseModel):
    message: str
    
    class Config:
        extra = 'forbid'

# 기본 주식 데이터 모델들을 Dict로 대체
StockHistoryData = Dict[str, Any]
StockInfoData = Dict[str, Any]
StockActionData = Dict[str, Any]
FinancialsData = Dict[str, Any]
HolderData = Dict[str, Any]
RecommendationData = Dict[str, Any]

# ==============================================================================
# 1-2. 데이터베이스 설정 (FinDB 연결)
# ==============================================================================

from models import get_db, Stock, DailyPrice, TechnicalIndicator, MarketIndex, MarketStat

# ==============================================================================
# 1-3. API 파라미터용 Enum 정의
# ==============================================================================

class FinancialType(str, Enum):
    income_stmt = "income_stmt"
    quarterly_income_stmt = "quarterly_income_stmt"
    balance_sheet = "balance_sheet"
    quarterly_balance_sheet = "quarterly_balance_sheet"
    cashflow = "cashflow"
    quarterly_cashflow = "quarterly_cashflow"

class HolderType(str, Enum):
    major_holders = "major_holders"
    institutional_holders = "institutional_holders"
    mutualfund_holders = "mutualfund_holders"
    insider_transactions = "insider_transactions"
    insider_purchases = "insider_purchases"
    insider_roster_holders = "insider_roster_holders"

class RecommendationType(str, Enum):
    recommendations = "recommendations"
    upgrades_downgrades = "upgrades_downgrades"

# ==============================================================================
# 2. FastAPI 애플리케이션 및 헬퍼 함수 정의
# ==============================================================================

app = FastAPI(
    title="Yahoo Finance API Server",
    description="분리된 yfinance 라이브러리 기반 금융 데이터 API",
    version="2.0.0",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAPI 3.0.3 스키마 설정
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    openapi_schema["openapi"] = "3.0.3"
    
    # 서버 정보 - 환경변수로 설정
    openapi_schema["servers"] = [
        {
            "url": os.getenv("API_SERVER_URL", "http://localhost:8000"),
            "description": "Yahoo Finance API Server"
        }
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

common_responses = {
    404: {"model": Message, "description": "Ticker not found"},
    500: {"model": Message, "description": "Internal Server Error"},
}

def get_stock_by_symbol(db: SQLSession, symbol: str) -> Stock:
    """Helper function to get a Stock object from database."""
    stock = db.query(Stock).filter(Stock.symbol == symbol.upper(), Stock.is_active == True).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock '{symbol}' not found in database.")
    return stock

# Helper function removed - no longer needed for database queries

# ==============================================================================
# 3. API 엔드포인트
# ==============================================================================

@app.get("/", summary="API 상태 확인")
def root():
    return {"message": "Yahoo Finance API Server is running", "version": "2.0.0"}

@app.get("/health", summary="헬스체크")
def health_check():
    return {"status": "healthy", "service": "yahoo-finance-api"}

@app.get("/stock/history", summary="주식 과거 시세 조회", response_model=List[StockHistoryData], responses=common_responses)
def get_historical_stock_prices(
    ticker: str = Query(..., description="조회할 주식의 티커", example="005930.KS"),
    days: int = Query(30, description="조회할 일수", example=365),
    db: SQLSession = Depends(get_db)
):
    try:
        stock = get_stock_by_symbol(db, ticker)
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        prices = db.query(DailyPrice).filter(
            DailyPrice.stock_id == stock.stock_id,
            DailyPrice.date >= start_date,
            DailyPrice.date <= end_date
        ).order_by(DailyPrice.date.desc()).all()
        
        result = []
        for price in prices:
            result.append({
                "Date": price.date.isoformat(),
                "Open": price.open_price,
                "High": price.high_price,
                "Low": price.low_price,
                "Close": price.close_price,
                "Adj_Close": price.adjusted_close,
                "Volume": price.volume,
                "Change": price.change,
                "Change_Rate": price.change_rate
            })
        
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stock/info", summary="주식 종합 정보 조회", response_model=StockInfoData, responses=common_responses)
def get_stock_info(ticker: str = Query(..., description="조회할 주식의 티커", example="005930.KS"), db: SQLSession = Depends(get_db)):
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

@app.get("/stock/actions", summary="주식 활동(배당, 분할) 조회", response_model=List[StockActionData], responses=common_responses)
def get_stock_actions(ticker: str = Query(..., description="조회할 주식의 티커", example="005930.KS"), db: SQLSession = Depends(get_db)):
    try:
        stock = get_stock_by_symbol(db, ticker)
        
        # 데이터베이스에 배당/분할 데이터가 없으므로 빈 리스트 반환
        return []
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stock/financials", summary="재무제표 조회", response_model=List[FinancialsData], responses=common_responses)
def get_financial_statement(
    ticker: str = Query(..., description="조회할 주식의 티커", example="005930.KS"),
    financial_type: FinancialType = Query(..., description="조회할 재무제표 종류", example="income_stmt"),
    db: SQLSession = Depends(get_db)
):
    try:
        stock = get_stock_by_symbol(db, ticker)
        
        # 데이터베이스에 재무제표 데이터가 없으므로 빈 리스트 반환
        return []
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stock/holders", summary="주주 정보 조회", response_model=List[HolderData], responses=common_responses)
def get_holder_info(
    ticker: str = Query(..., description="조회할 주식의 티커", example="005930.KS"),
    holder_type: HolderType = Query(..., description="조회할 주주 정보 종류", example="major_holders"),
    db: SQLSession = Depends(get_db)
):
    try:
        stock = get_stock_by_symbol(db, ticker)
        
        # 데이터베이스에 주주 정보가 없으므로 빈 리스트 반환
        return []
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stock/recommendations", summary="애널리스트 추천 정보 조회", response_model=List[RecommendationData], responses=common_responses)
def get_recommendations(
    ticker: str = Query(..., description="조회할 주식의 티커", example="005930.KS"),
    recommendation_type: RecommendationType = Query("recommendations", description="조회할 추천 정보 종류", example="upgrades_downgrades"),
    months_back: int = Query(12, description="upgrades_downgrades 조회 시, 과거 몇 개월까지의 데이터를 볼지 설정", ge=1),
    db: SQLSession = Depends(get_db)
):
    try:
        stock = get_stock_by_symbol(db, ticker)
        
        # 데이터베이스에 추천 정보가 없으므로 빈 리스트 반환
        return []
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)