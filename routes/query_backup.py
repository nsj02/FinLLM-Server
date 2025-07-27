# routes/query.py - 통합 쿼리 API 라우터

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session as SQLSession
from sqlalchemy import desc, asc, and_, or_
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from models import get_db, Stock, DailyPrice, MarketStat, MarketIndex, TechnicalIndicator
from utils.helpers import parse_date, common_responses

router = APIRouter()

def find_stock_by_name(db: SQLSession, stock_name: str, market: str = "ALL"):
    """종목명으로 종목 검색 (자동 매칭)"""
    base_query = db.query(Stock).filter(Stock.is_active == True)
    
    if market != "ALL":
        base_query = base_query.filter(Stock.market == market)
    
    # 정확한 매칭 우선
    exact_match = base_query.filter(Stock.name == stock_name).first()
    if exact_match:
        return exact_match
    
    # 부분 매칭
    partial_match = base_query.filter(
        (Stock.name.contains(stock_name)) | 
        (Stock.symbol.contains(stock_name)) |
        (Stock.krx_code.contains(stock_name))
    ).first()
    
    return partial_match

# =============================================================================
# 1. Simple Queries API
# =============================================================================

@router.get("/query/simple", summary="간단 조회 (Simple Queries)")
def simple_query(
    # 종목 가격 조회
    stock: Optional[str] = Query(None, description="종목명 또는 종목코드", examples=["동부건설우", "005965.KS"]),
    date: Optional[str] = Query(None, description="조회 날짜 (YYYY-MM-DD)", examples=["2024-11-06"]),
    price_type: str = Query("close", description="가격 유형 (open/high/low/close/change_rate)", examples=["open"]),
    
    # 시장 통계 조회
    stat_type: Optional[str] = Query(None, description="통계 유형 (rising_count/falling_count/market_count/total_value/index)", examples=["rising_count"]),
    
    # 시장 순위 조회  
    rank_type: Optional[str] = Query(None, description="순위 기준 (change_rate/volume/close_price)", examples=["change_rate"]),
    direction: str = Query("desc", description="정렬 방향 (desc=높은순/asc=낮은순)", examples=["desc"]),
    limit: int = Query(5, description="조회 개수", examples=[5]),
    
    # 공통 파라미터
    market: str = Query("ALL", description="시장 (KOSPI/KOSDAQ/ALL)", examples=["ALL"]),
    db: SQLSession = Depends(get_db)
):
    """Simple Queries 처리 - 단일 종목 조회, 시장 통계, 순위 조회"""
    try:
        if not date:
            raise HTTPException(status_code=400, detail="date 파라미터가 필요합니다")
            
        query_date = parse_date(date).date()
        
        # 1. 종목 가격 조회
        if stock:
            found_stock = find_stock_by_name(db, stock, market)
            if not found_stock:
                raise HTTPException(status_code=404, detail=f"종목을 찾을 수 없습니다: {stock}")
            
            price_data = db.query(DailyPrice).filter(
                DailyPrice.stock_id == found_stock.stock_id,
                DailyPrice.date == query_date
            ).first()
            
            if not price_data:
                return {
                    "query_type": "stock_price",
                    "stock_name": found_stock.name,
                    "symbol": found_stock.symbol,
                    "market": found_stock.market,
                    "date": date,
                    "message": "해당 날짜 데이터 없음",
                    "formatted_answer": "해당 날짜 데이터 없음"
                }
            
            price_map = {
                "open": price_data.open_price,
                "high": price_data.high_price,
                "low": price_data.low_price,
                "close": price_data.close_price,
                "change_rate": price_data.change_rate
            }
            
            requested_price = price_map.get(price_type, price_data.close_price)
            
            if price_type == "change_rate":
                formatted_price = f"{requested_price:.2f}%"
            else:
                formatted_price = f"{requested_price:,.0f}원"
            
            return {
                "query_type": "stock_price",
                "stock_name": found_stock.name,
                "symbol": found_stock.symbol,
                "market": found_stock.market,
                "date": date,
                "price_type": price_type,
                "price": requested_price,
                "formatted_answer": formatted_price
            }
        
        # 2. 시장 통계 조회
        elif stat_type:
            if stat_type == "index":
                # KOSPI/KOSDAQ 지수 조회
                target_market = "KOSPI" if market == "ALL" else market
                market_index = db.query(MarketIndex).filter(
                    MarketIndex.date == query_date,
                    MarketIndex.market == target_market
                ).first()
                
                if not market_index:
                    raise HTTPException(status_code=404, detail=f"{target_market} 지수 데이터 없음: {date}")
                
                return {
                    "query_type": "market_index",
                    "date": date,
                    "market": target_market,
                    "index": market_index.close_index,
                    "formatted_answer": f"{market_index.close_index:.2f}"
                }
            
            else:
                # 시장 통계 조회
                if market == "ALL":
                    kospi_stat = db.query(MarketStat).filter(
                        MarketStat.date == query_date,
                        MarketStat.market == "KOSPI"
                    ).first()
                    
                    kosdaq_stat = db.query(MarketStat).filter(
                        MarketStat.date == query_date,
                        MarketStat.market == "KOSDAQ"  
                    ).first()
                    
                    if not kospi_stat and not kosdaq_stat:
                        raise HTTPException(status_code=404, detail=f"시장 통계 데이터 없음: {date}")
                    
                    rising = (kospi_stat.rising_stocks if kospi_stat else 0) + (kosdaq_stat.rising_stocks if kosdaq_stat else 0)
                    falling = (kospi_stat.falling_stocks if kospi_stat else 0) + (kosdaq_stat.falling_stocks if kosdaq_stat else 0)
                    total = (kospi_stat.total_stocks if kospi_stat else 0) + (kosdaq_stat.total_stocks if kosdaq_stat else 0)
                    value = (kospi_stat.total_value if kospi_stat else 0) + (kosdaq_stat.total_value if kosdaq_stat else 0)
                    
                else:
                    market_stat = db.query(MarketStat).filter(
                        MarketStat.date == query_date,
                        MarketStat.market == market
                    ).first()
                    
                    if not market_stat:
                        raise HTTPException(status_code=404, detail=f"{market} 시장 통계 없음: {date}")
                    
                    rising = market_stat.rising_stocks
                    falling = market_stat.falling_stocks
                    total = market_stat.total_stocks
                    value = market_stat.total_value
                
                stat_map = {
                    "rising_count": rising,
                    "falling_count": falling,
                    "market_count": total,
                    "total_value": value
                }
                
                result_value = stat_map.get(stat_type, rising)
                
                if stat_type == "total_value":
                    formatted_answer = f"{result_value:,.0f}원"
                else:
                    formatted_answer = f"{result_value:,}개"
                
                return {
                    "query_type": "market_stats",
                    "date": date,
                    "market": market,
                    "stat_type": stat_type,
                    "value": result_value,
                    "formatted_answer": formatted_answer
                }
        
        # 3. 시장 순위 조회
        elif rank_type:
            target_market = market if market != "ALL" else "KOSPI"
            
            query = db.query(DailyPrice, Stock).join(Stock, DailyPrice.stock_id == Stock.stock_id).filter(
                DailyPrice.date == query_date,
                Stock.market == target_market,
                Stock.is_active == True
            )
            
            sort_columns = {
                "change_rate": DailyPrice.change_rate,
                "volume": DailyPrice.volume,
                "close_price": DailyPrice.close_price
            }
            sort_column = sort_columns.get(rank_type, DailyPrice.change_rate)
            
            if direction == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
            
            results = query.limit(limit).all()
            
            if not results:
                raise HTTPException(status_code=404, detail=f"{target_market} 시장 데이터 없음: {date}")
            
            rankings = []
            for i, (price, stock) in enumerate(results, 1):
                ranking_value = getattr(price, rank_type)
                
                if rank_type == "change_rate":
                    formatted_value = f"{ranking_value:.2f}%"
                elif rank_type == "volume":
                    formatted_value = f"({ranking_value:,}주)"
                else:
                    formatted_value = f"{ranking_value:,}원"
                
                rankings.append({
                    "rank": i,
                    "name": stock.name,
                    "symbol": stock.symbol,
                    "value": ranking_value,
                    "formatted": f"{stock.name} {formatted_value}" if rank_type == "volume" else stock.name
                })
            
            simple_list = [item["formatted"] for item in rankings]
            
            return {
                "query_type": "market_rankings",
                "date": date,
                "market": target_market,
                "rank_type": rank_type,
                "rankings": rankings,
                "formatted_answer": ", ".join(simple_list)
            }
        
        else:
            raise HTTPException(status_code=400, detail="stock, stat_type, rank_type 중 하나는 필수입니다")
            
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# 2. Conditional Queries API  
# =============================================================================

@router.get("/query/filter", summary="조건 검색 (Conditional Queries)")
def conditional_query(
    date: str = Query(..., description="조회 날짜 (YYYY-MM-DD)", examples=["2025-05-14"]),
    
    # 거래량 조건
    volume_change_min: Optional[float] = Query(None, description="거래량 변화율 최소값 (%)", examples=[300]),
    volume_min: Optional[int] = Query(None, description="최소 거래량 (주)", examples=[20000000]),
    
    # 등락률 조건
    change_rate_min: Optional[float] = Query(None, description="등락률 최소값 (%)", examples=[5]),
    change_rate_max: Optional[float] = Query(None, description="등락률 최대값 (%)", examples=[100]),
    
    # 가격 조건
    price_min: Optional[float] = Query(None, description="최소 종가 (원)", examples=[100000]),
    price_max: Optional[float] = Query(None, description="최대 종가 (원)", examples=[200000]),
    
    # 공통 파라미터
    market: str = Query("ALL", description="시장 (KOSPI/KOSDAQ/ALL)", examples=["ALL"]),
    limit: int = Query(50, description="조회 개수", examples=[20]),
    db: SQLSession = Depends(get_db)
):
    """Conditional Queries 처리 - 복합 조건 검색"""
    try:
        query_date = parse_date(date).date()
        prev_date = query_date - timedelta(days=1)
        
        # 기본 쿼리
        base_query = db.query(DailyPrice, Stock).join(Stock, DailyPrice.stock_id == Stock.stock_id).filter(
            DailyPrice.date == query_date,
            Stock.is_active == True
        )
        
        # 시장 필터
        if market != "ALL":
            base_query = base_query.filter(Stock.market == market)
        
        # 등락률 조건
        if change_rate_min is not None:
            base_query = base_query.filter(DailyPrice.change_rate >= change_rate_min)
        if change_rate_max is not None:
            base_query = base_query.filter(DailyPrice.change_rate <= change_rate_max)
        
        # 가격 조건
        if price_min is not None:
            base_query = base_query.filter(DailyPrice.close_price >= price_min)
        if price_max is not None:
            base_query = base_query.filter(DailyPrice.close_price <= price_max)
        
        # 절대 거래량 조건
        if volume_min is not None:
            base_query = base_query.filter(DailyPrice.volume >= volume_min)
        
        results = []
        
        for current_price, stock in base_query.all():
            # 거래량 변화율 조건 확인
            if volume_change_min is not None:
                prev_price = db.query(DailyPrice).filter(
                    DailyPrice.stock_id == stock.stock_id,
                    DailyPrice.date == prev_date
                ).first()
                
                if prev_price and prev_price.volume > 0:
                    volume_change = ((current_price.volume - prev_price.volume) / prev_price.volume) * 100
                    if volume_change < volume_change_min:
                        continue
                else:
                    continue
            
            results.append({
                "name": stock.name,
                "symbol": stock.symbol,
                "market": stock.market,
                "close_price": current_price.close_price,
                "change_rate": current_price.change_rate,
                "volume": current_price.volume
            })
        
        # 등락률 기준 정렬
        results.sort(key=lambda x: x["change_rate"], reverse=True)
        results = results[:limit]
        
        # 종목명만 추출
        stock_names = [item["name"] for item in results]
        
        return {
            "query_type": "conditional_filter",
            "date": date,
            "market": market,
            "conditions": {
                "volume_change_min": volume_change_min,
                "volume_min": volume_min,
                "change_rate_min": change_rate_min,
                "change_rate_max": change_rate_max,
                "price_min": price_min,
                "price_max": price_max
            },
            "results": results,
            "stock_names": stock_names,
            "formatted_answer": ", ".join(stock_names) if stock_names else "조건에 맞는 종목 없음"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# 3. Signal Queries API
# =============================================================================

@router.get("/query/signal", summary="기술적 신호 (Signal Queries)")
def signal_query(
    # 기본 파라미터
    date: Optional[str] = Query(None, description="조회 날짜 (YYYY-MM-DD)", examples=["2025-01-20"]),
    signal_type: str = Query(..., description="신호 유형", examples=["rsi_overbought"]),
    
    # RSI 관련
    threshold: Optional[float] = Query(None, description="RSI/기타 임계값", examples=[70]),
    
    # 거래량 급증 관련
    volume_multiplier: Optional[float] = Query(None, description="거래량 배수 (예: 5.0 = 500%)", examples=[5.0]),
    
    # 이동평균 관련
    ma_period: Optional[int] = Query(None, description="이동평균 기간", examples=[20]),
    breakout_percent: Optional[float] = Query(None, description="돌파 비율 (%)", examples=[3.0]),
    
    # 기간 관련
    period: int = Query(20, description="기간 (일)", examples=[20]),
    limit: int = Query(15, description="조회 개수", examples=[15]),
    
    # 크로스 신호용 파라미터
    stock: Optional[str] = Query(None, description="특정 종목 (크로스 횟수 조회용)", examples=["현대백화점"]),
    start_date: Optional[str] = Query(None, description="시작 날짜 (크로스 횟수 조회용)", examples=["2024-06-01"]),
    end_date: Optional[str] = Query(None, description="종료 날짜 (크로스 횟수 조회용)", examples=["2025-06-30"]),
    
    db: SQLSession = Depends(get_db)
):
    """Signal Queries 처리 - 기술적 분석 신호"""
    try:
        # 크로스 횟수 조회 (특정 종목 + 기간)
        if signal_type.endswith("_count") and stock and start_date and end_date:
            stock_obj = find_stock_by_name(db, stock)
            if not stock_obj:
                raise HTTPException(status_code=404, detail=f"종목을 찾을 수 없습니다: {stock}")
            
            start_dt = parse_date(start_date).date()
            end_dt = parse_date(end_date).date()
            
            # 기술적 지표 데이터 조회 (기간 내)
            tech_data = db.query(TechnicalIndicator).filter(
                TechnicalIndicator.stock_id == stock_obj.stock_id,
                TechnicalIndicator.date >= start_dt,
                TechnicalIndicator.date <= end_dt,
                TechnicalIndicator.ma5.isnot(None),
                TechnicalIndicator.ma20.isnot(None)
            ).order_by(TechnicalIndicator.date).all()
            
            golden_cross_count = 0
            dead_cross_count = 0
            
            for i in range(1, len(tech_data)):
                prev = tech_data[i-1]
                curr = tech_data[i]
                
                # 골든크로스: 5일선이 20일선을 상향 돌파
                if prev.ma5 <= prev.ma20 and curr.ma5 > curr.ma20:
                    golden_cross_count += 1
                
                # 데드크로스: 5일선이 20일선을 하향 돌파
                if prev.ma5 >= prev.ma20 and curr.ma5 < curr.ma20:
                    dead_cross_count += 1
            
            if signal_type == "golden_cross_count":
                return {
                    "query_type": "signal_count",
                    "stock": stock,
                    "signal_type": signal_type,
                    "start_date": start_date,
                    "end_date": end_date,
                    "count": golden_cross_count,
                    "formatted_answer": f"{golden_cross_count}번"
                }
            elif signal_type == "dead_cross_count":
                return {
                    "query_type": "signal_count", 
                    "stock": stock,
                    "signal_type": signal_type,
                    "start_date": start_date,
                    "end_date": end_date,
                    "count": dead_cross_count,
                    "formatted_answer": f"{dead_cross_count}번"
                }
            else:  # 통합 (데드크로스 + 골든크로스)
                return {
                    "query_type": "signal_count",
                    "stock": stock,
                    "signal_type": signal_type,
                    "start_date": start_date,
                    "end_date": end_date,
                    "dead_cross": dead_cross_count,
                    "golden_cross": golden_cross_count,
                    "formatted_answer": f"데드크로스 {dead_cross_count}번, 골든크로스 {golden_cross_count}번"
                }
        
        # 일반 신호 조회 (날짜 필수)
        if not date:
            raise HTTPException(status_code=400, detail="date parameter required for signal detection")
        
        query_date = parse_date(date).date()
        
        if signal_type.startswith("rsi_"):
            # RSI 신호
            base_query = db.query(TechnicalIndicator, Stock).join(
                Stock, TechnicalIndicator.stock_id == Stock.stock_id
            ).filter(
                TechnicalIndicator.date == query_date,
                Stock.is_active == True,
                TechnicalIndicator.rsi.isnot(None)
            )
            
            if signal_type == "rsi_overbought":
                threshold_val = threshold or 70
                query = base_query.filter(TechnicalIndicator.rsi >= threshold_val)
                order_by = desc(TechnicalIndicator.rsi)
            elif signal_type == "rsi_oversold":
                threshold_val = threshold or 30
                query = base_query.filter(TechnicalIndicator.rsi <= threshold_val)
                order_by = asc(TechnicalIndicator.rsi)
            
            results = query.order_by(order_by).limit(limit).all()
            
            formatted_results = []
            for tech, stock in results:
                formatted_results.append({
                    "name": stock.name,
                    "symbol": stock.symbol,
                    "rsi": tech.rsi,
                    "formatted": f"{stock.name}(RSI:{tech.rsi:.1f})"
                })
            
            answer_list = [item["formatted"] for item in formatted_results]
            
        elif signal_type == "volume_surge":
            # 거래량 급증 신호
            multiplier = volume_multiplier or 1.0
            
            current_query = db.query(DailyPrice, Stock).join(
                Stock, DailyPrice.stock_id == Stock.stock_id
            ).filter(
                DailyPrice.date == query_date,
                Stock.is_active == True
            )
            
            results = []
            for current_price, stock in current_query.all():
                # 20일 평균 거래량 계산
                avg_volume_query = db.query(DailyPrice).filter(
                    DailyPrice.stock_id == stock.stock_id,
                    DailyPrice.date <= query_date - timedelta(days=1),
                    DailyPrice.date >= query_date - timedelta(days=period)
                ).all()
                
                if len(avg_volume_query) >= 10:
                    avg_volume = sum(p.volume for p in avg_volume_query) / len(avg_volume_query)
                    if avg_volume > 0:
                        surge_ratio = (current_price.volume / avg_volume) * 100
                        if surge_ratio >= multiplier * 100:
                            results.append({
                                "name": stock.name,
                                "symbol": stock.symbol,
                                "surge_ratio": surge_ratio,
                                "formatted": f"{stock.name}({surge_ratio:.0f}%)"
                            })
            
            results.sort(key=lambda x: x["surge_ratio"], reverse=True)
            results = results[:limit]
            formatted_results = results
            answer_list = [item["formatted"] for item in results]
            
        elif signal_type.startswith("bollinger_"):
            # 볼린저밴드 신호
            base_query = db.query(TechnicalIndicator, Stock).join(
                Stock, TechnicalIndicator.stock_id == Stock.stock_id
            ).filter(
                TechnicalIndicator.date == query_date,
                Stock.is_active == True,
                TechnicalIndicator.bb_upper_touch.isnot(None)
            )
            
            if signal_type == "bollinger_upper":
                query = base_query.filter(TechnicalIndicator.bb_upper_touch == True)
            elif signal_type == "bollinger_lower":
                query = base_query.filter(TechnicalIndicator.bb_lower_touch == True)
            
            results = query.limit(limit).all()
            formatted_results = []
            for tech, stock in results:
                formatted_results.append({
                    "name": stock.name,
                    "symbol": stock.symbol,
                    "formatted": stock.name
                })
            
            answer_list = [item["name"] for item in formatted_results]
            
        elif signal_type == "ma_breakout":
            # 이동평균선 돌파 신호
            ma_period_val = ma_period or 20
            breakout_percent_val = breakout_percent or 3.0
            
            query = db.query(TechnicalIndicator, DailyPrice, Stock).join(
                DailyPrice, and_(
                    TechnicalIndicator.stock_id == DailyPrice.stock_id,
                    TechnicalIndicator.date == DailyPrice.date
                )
            ).join(
                Stock, TechnicalIndicator.stock_id == Stock.stock_id
            ).filter(
                TechnicalIndicator.date == query_date,
                Stock.is_active == True
            )
            
            results = []
            for tech, price, stock in query.all():
                ma_value = None
                if ma_period_val == 5:
                    ma_value = tech.ma5
                elif ma_period_val == 20:
                    ma_value = tech.ma20
                elif ma_period_val == 60:
                    ma_value = tech.ma60
                
                if ma_value and price.close_price:
                    deviation = ((price.close_price - ma_value) / ma_value) * 100
                    if deviation >= breakout_percent_val:
                        results.append({
                            "name": stock.name,
                            "symbol": stock.symbol,
                            "deviation": deviation,
                            "formatted": f"{stock.name}({deviation:.2f}%)"
                        })
            
            results.sort(key=lambda x: x["deviation"], reverse=True)
            results = results[:limit]
            formatted_results = results
            answer_list = [item["formatted"] for item in results]
            
        else:
            raise HTTPException(status_code=400, detail=f"지원하지 않는 신호 유형: {signal_type}")
        
        return {
            "query_type": "signal_detection",
            "date": date,
            "signal_type": signal_type,
            "threshold": threshold,
            "volume_multiplier": volume_multiplier,
            "results": formatted_results,
            "formatted_answer": ", ".join(answer_list) if answer_list else "조건에 맞는 종목 없음"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))