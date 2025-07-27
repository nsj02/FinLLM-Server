# routes/query.py - 통합 쿼리 API 라우터 (수정된 버전)

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
    try:
        base_query = db.query(Stock).filter(Stock.is_active == True)
        
        if market != "ALL":
            base_query = base_query.filter(Stock.market == market)
        
        # 정확한 매칭 우선
        exact_match = base_query.filter(Stock.name == stock_name).first()
        if exact_match:
            print(f"정확 매칭 성공: {stock_name} -> {exact_match.name}")
            return exact_match
        
        # 심볼로도 찾기 (282720.KQ 같은 형태)
        symbol_match = base_query.filter(Stock.symbol == stock_name).first()
        if symbol_match:
            print(f"심볼 매칭 성공: {stock_name} -> {symbol_match.name}")
            return symbol_match
            
        # KRX 코드로도 찾기 (282720 같은 형태)
        krx_match = base_query.filter(Stock.krx_code == stock_name).first()
        if krx_match:
            print(f"KRX 코드 매칭 성공: {stock_name} -> {krx_match.name}")
            return krx_match
        
        # 부분 매칭
        partial_match = base_query.filter(
            (Stock.name.contains(stock_name)) | 
            (Stock.symbol.contains(stock_name)) |
            (Stock.krx_code.contains(stock_name))
        ).first()
        
        if partial_match:
            print(f"부분 매칭 성공: {stock_name} -> {partial_match.name}")
            return partial_match
        
        # 전체 종목에서 유사한 이름 찾기
        all_stocks = db.query(Stock.name).filter(Stock.is_active == True).all()
        similar_names = [s.name for s in all_stocks if stock_name in s.name or s.name in stock_name]
        print(f"검색 실패: '{stock_name}', 유사한 종목: {similar_names[:5]}")
        
        return None
    except Exception as e:
        print(f"종목 검색 중 오류: {e}")
        return None

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
    direction: str = Query("desc", description="정렬 방향 (desc/asc)", examples=["desc"]),
    
    # 공통 파라미터
    market: str = Query("KOSPI", description="시장 (KOSPI/KOSDAQ/ALL)", examples=["KOSPI"]),
    limit: int = Query(5, description="조회 개수", examples=[5]),
    db: SQLSession = Depends(get_db)
):
    """Simple Queries 처리 - 개별 종목, 시장 통계, 순위 조회"""
    try:
        # 1. 개별 종목 가격 조회
        if stock and date:
            query_date = parse_date(date).date()
            
            # 다양한 방법으로 종목 검색
            stock_obj = None
            
            # 정확한 종목명 매칭
            stock_obj = db.query(Stock).filter(Stock.name == stock, Stock.is_active == True).first()
            
            # 심볼 매칭 (282720.KQ 등)
            if not stock_obj:
                stock_obj = db.query(Stock).filter(Stock.symbol == stock, Stock.is_active == True).first()
            
            # KRX 코드 매칭 (282720 등)  
            if not stock_obj:
                stock_obj = db.query(Stock).filter(Stock.krx_code == stock, Stock.is_active == True).first()
            
            # 부분 매칭
            if not stock_obj:
                stock_obj = db.query(Stock).filter(
                    (Stock.name.contains(stock)) | 
                    (Stock.symbol.contains(stock)) |
                    (Stock.krx_code.contains(stock)),
                    Stock.is_active == True
                ).first()
            
            if not stock_obj:
                raise HTTPException(status_code=404, detail=f"종목을 찾을 수 없습니다: {stock}")
            
            price_data = db.query(DailyPrice).filter(
                DailyPrice.stock_id == stock_obj.stock_id,
                DailyPrice.date == query_date
            ).first()
            
            if not price_data:
                raise HTTPException(status_code=404, detail=f"가격 데이터 없음: {stock} ({date})")
            
            price_map = {
                "open": price_data.open_price,
                "high": price_data.high_price,
                "low": price_data.low_price,
                "close": price_data.close_price,
                "change_rate": price_data.change_rate
            }
            
            value = price_map.get(price_type, price_data.close_price)
            
            if price_type == "change_rate":
                formatted_answer = f"{value:+.2f}%" if value else "0.00%"
            elif value == 0:
                formatted_answer = "0원"
            else:
                formatted_answer = f"{value:,.0f}원" if value else "데이터 없음"
            
            return {
                "query_type": "individual_price",
                "stock": stock,
                "date": date,
                "price_type": price_type,
                "value": value,
                "formatted_answer": formatted_answer
            }
        
        # 2. 시장 통계 조회
        elif stat_type and date:
            query_date = parse_date(date).date()
            
            if stat_type == "index":
                # 지수 조회
                if market == "ALL":
                    raise HTTPException(status_code=400, detail="지수 조회시에는 특정 시장(KOSPI/KOSDAQ)을 선택해야 합니다")
                
                index_data = db.query(MarketIndex).filter(
                    MarketIndex.date == query_date,
                    MarketIndex.market == market
                ).first()
                
                if not index_data:
                    raise HTTPException(status_code=404, detail=f"{market} 지수 데이터 없음: {date}")
                
                return {
                    "query_type": "market_index",
                    "date": date,
                    "market": market,
                    "value": index_data.index_value,
                    "formatted_answer": f"{index_data.index_value:,.2f}"
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
                DailyPrice.date == parse_date(date).date(),
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
            
            stock_list = []
            for price, stock in results:
                if rank_type == "volume":
                    stock_list.append(f"{stock.name} ({price.volume:,}주)")
                elif rank_type == "change_rate":
                    stock_list.append(f"{stock.name}")
                else:
                    stock_list.append(f"{stock.name}")
            
            return {
                "query_type": "market_ranking",
                "date": date,
                "market": target_market,
                "rank_type": rank_type,
                "direction": direction,
                "limit": limit,
                "results": stock_list,
                "formatted_answer": ", ".join(stock_list)
            }
        
        else:
            raise HTTPException(status_code=400, detail="올바른 파라미터를 제공해주세요")
        
    except Exception as e:
        import traceback
        error_detail = f"Error: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(f"API Error: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)

# =============================================================================
# 2. Filter Queries API (완전 구현)
# =============================================================================

@router.get("/query/filter", summary="조건 검색 (Filter Queries)")
def filter_query(
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
    """Filter Queries 처리 - 복합 조건 검색"""
    try:
        query_date = parse_date(date).date()
        
        # 기본 쿼리
        base_query = db.query(DailyPrice, Stock).join(Stock, DailyPrice.stock_id == Stock.stock_id).filter(
            DailyPrice.date == query_date,
            Stock.is_active == True
        )
        
        # 시장 필터
        if market != "ALL":
            base_query = base_query.filter(Stock.market == market)
        
        results = []
        
        for price, stock in base_query.all():
            # 등락률 조건 체크
            if change_rate_min is not None and (price.change_rate is None or price.change_rate < change_rate_min):
                continue
            if change_rate_max is not None and (price.change_rate is None or price.change_rate > change_rate_max):
                continue
            
            # 가격 조건 체크
            if price_min is not None and (price.close_price is None or price.close_price < price_min):
                continue
            if price_max is not None and (price.close_price is None or price.close_price > price_max):
                continue
            
            # 거래량 절대값 조건 체크
            if volume_min is not None and (price.volume is None or price.volume < volume_min):
                continue
            
            # 거래량 변화율 조건 체크
            if volume_change_min is not None:
                prev_date = query_date - timedelta(days=1)
                prev_price = db.query(DailyPrice).filter(
                    DailyPrice.stock_id == price.stock_id,
                    DailyPrice.date == prev_date
                ).first()
                
                if not prev_price or prev_price.volume == 0:
                    continue
                
                volume_change = ((price.volume - prev_price.volume) / prev_price.volume) * 100
                if volume_change < volume_change_min:
                    continue
            
            # 조건을 만족하는 종목 추가
            results.append({
                "name": stock.name,
                "symbol": stock.symbol,
                "market": stock.market,
                "close_price": price.close_price,
                "change_rate": price.change_rate,
                "volume": price.volume
            })
        
        # 등락률 기준 정렬
        results.sort(key=lambda x: x["change_rate"] or 0, reverse=True)
        results = results[:limit]
        
        stock_names = [item["name"] for item in results]
        formatted_answer = ", ".join(stock_names) if stock_names else "조건에 맞는 종목 없음"
        
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
            "formatted_answer": formatted_answer
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# 3. Signal Queries API (완전 구현)
# =============================================================================

@router.get("/query/signal", summary="기술적 신호 (Signal Queries)")
def signal_query(
    # 기본 파라미터
    date: Optional[str] = Query(None, description="조회 날짜 (YYYY-MM-DD)", examples=["2025-01-20"]),
    signal_type: str = Query(..., description="신호 유형", examples=["rsi_overbought"]),
    
    # RSI 파라미터
    threshold: Optional[float] = Query(None, description="RSI 임계값 (70=과매수, 30=과매도)", examples=[70]),
    
    # 거래량 급증 파라미터
    volume_multiplier: Optional[float] = Query(None, description="거래량 배수 (예: 5.0 = 500%)", examples=[5.0]),
    
    # 이동평균 돌파 파라미터
    ma_period: Optional[int] = Query(None, description="이동평균 기간 (5/20/60일)", examples=[20]),
    breakout_percent: Optional[float] = Query(None, description="돌파 비율 (%)", examples=[10.0]),
    
    # 크로스 신호 파라미터 (기간별 횟수 조회용)
    stock: Optional[str] = Query(None, description="특정 종목명 (크로스 횟수 조회용)", examples=["현대백화점"]),
    start_date: Optional[str] = Query(None, description="시작 날짜 (크로스 횟수 조회용)", examples=["2024-06-01"]),
    end_date: Optional[str] = Query(None, description="종료 날짜 (크로스 횟수 조회용)", examples=["2025-06-30"]),
    
    # 공통 파라미터
    period: int = Query(20, description="분석 기간 (일)", examples=[20]),
    limit: int = Query(15, description="조회 개수", examples=[15]),
    db: SQLSession = Depends(get_db)
):
    """Signal Queries 처리 - 기술적 분석 신호"""
    try:
        # 크로스 횟수 조회 (특정 종목의 기간별 크로스 발생 횟수)
        if signal_type.endswith("_count") or (stock and start_date and end_date):
            if not stock or not start_date or not end_date:
                raise HTTPException(status_code=400, detail="크로스 횟수 조회에는 stock, start_date, end_date가 모두 필요합니다")
            
            stock_obj = find_stock_by_name(db, stock)
            if not stock_obj:
                raise HTTPException(status_code=404, detail=f"종목을 찾을 수 없습니다: {stock}")
            
            start_dt = parse_date(start_date).date()
            end_dt = parse_date(end_date).date()
            
            # 해당 기간의 기술적 지표 데이터 조회
            tech_data = db.query(TechnicalIndicator).filter(
                TechnicalIndicator.stock_id == stock_obj.stock_id,
                TechnicalIndicator.date.between(start_dt, end_dt),
                TechnicalIndicator.ma5.isnot(None),
                TechnicalIndicator.ma20.isnot(None)
            ).order_by(TechnicalIndicator.date).all()
            
            if len(tech_data) < 2:
                return {
                    "query_type": "cross_count",
                    "stock": stock,
                    "start_date": start_date,
                    "end_date": end_date,
                    "golden_cross_count": 0,
                    "dead_cross_count": 0,
                    "formatted_answer": "데이터 부족으로 크로스 신호를 분석할 수 없습니다"
                }
            
            golden_cross_count = 0
            dead_cross_count = 0
            
            for i in range(1, len(tech_data)):
                prev_data = tech_data[i-1]
                curr_data = tech_data[i]
                
                # 이전: MA5 <= MA20, 현재: MA5 > MA20 => 골든크로스
                if (prev_data.ma5 <= prev_data.ma20 and curr_data.ma5 > curr_data.ma20):
                    golden_cross_count += 1
                # 이전: MA5 >= MA20, 현재: MA5 < MA20 => 데드크로스
                elif (prev_data.ma5 >= prev_data.ma20 and curr_data.ma5 < curr_data.ma20):
                    dead_cross_count += 1
            
            if signal_type == "golden_cross_count":
                formatted_answer = f"{golden_cross_count}번"
            elif signal_type == "dead_cross_count":
                formatted_answer = f"{dead_cross_count}번"
            else:
                formatted_answer = f"데드크로스 {dead_cross_count}번, 골든크로스 {golden_cross_count}번"
            
            return {
                "query_type": "cross_count",
                "stock": stock,
                "start_date": start_date,
                "end_date": end_date,
                "signal_type": signal_type,
                "golden_cross_count": golden_cross_count,
                "dead_cross_count": dead_cross_count,
                "formatted_answer": formatted_answer
            }
        
        # 일반 신호 조회 (특정 날짜)
        if not date:
            raise HTTPException(status_code=400, detail="일반 신호 조회에는 date 파라미터가 필요합니다")
        
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
                threshold = threshold or 70
                query = base_query.filter(TechnicalIndicator.rsi >= threshold)
                order_by = desc(TechnicalIndicator.rsi)
            elif signal_type == "rsi_oversold":
                threshold = threshold or 30
                query = base_query.filter(TechnicalIndicator.rsi <= threshold)
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
            # 거래량 급증 신호 (20일 평균 대비)
            multiplier = volume_multiplier or 1.0  # 기본값 100% (1배)
            
            # 현재 날짜 데이터
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
                
                if len(avg_volume_query) >= 10:  # 최소 10일 데이터
                    avg_volume = sum(p.volume for p in avg_volume_query) / len(avg_volume_query)
                    if avg_volume > 0:
                        surge_ratio = (current_price.volume / avg_volume) * 100
                        if surge_ratio >= multiplier * 100:  # multiplier를 퍼센트로 변환
                            results.append({
                                "name": stock.name,
                                "symbol": stock.symbol,
                                "surge_ratio": surge_ratio,
                                "formatted": f"{stock.name}({surge_ratio:.0f}%)"
                            })
            
            # 급증률 기준 정렬
            results.sort(key=lambda x: x["surge_ratio"], reverse=True)
            results = results[:limit]
            
            formatted_results = results
            answer_list = [item["formatted"] for item in results]
            
        elif signal_type.startswith("bollinger_"):
            # 볼린저 밴드 신호
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
            ma_period_val = ma_period or 20  # 기본 20일
            breakout_percent_val = breakout_percent or 3.0  # 기본 3% 이상
            
            # 현재 날짜의 기술적 지표와 가격 데이터 조인
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
            
            # 돌파율 기준 정렬
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
            "ma_period": ma_period,
            "breakout_percent": breakout_percent,
            "results": formatted_results,
            "formatted_answer": ", ".join(answer_list) if answer_list else "조건에 맞는 종목 없음"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))