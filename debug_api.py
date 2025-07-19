#!/usr/bin/env python3
# debug_api.py - API 디버깅 스크립트

from models import SessionLocal, Stock, DailyPrice, MarketStat
from sqlalchemy import text
from datetime import datetime, date

def test_db_connection():
    """DB 연결 및 기본 쿼리 테스트"""
    db = SessionLocal()
    try:
        # 1. 테이블 존재 확인
        tables = db.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")).fetchall()
        print("존재하는 테이블:", [t[0] for t in tables])
        
        # 2. stocks 테이블 확인
        stock_count = db.query(Stock).count()
        print(f"총 주식 수: {stock_count}")
        
        # 3. 삼성전자 검색
        samsung = db.query(Stock).filter(Stock.symbol == '005930.KS').first()
        if samsung:
            print(f"삼성전자: {samsung.name}, ID: {samsung.stock_id}")
            
            # 4. 삼성전자 가격 데이터 확인
            price_count = db.query(DailyPrice).filter(DailyPrice.stock_id == samsung.stock_id).count()
            print(f"삼성전자 가격 데이터 수: {price_count}")
            
            # 5. 최신 가격 데이터
            latest_price = db.query(DailyPrice).filter(
                DailyPrice.stock_id == samsung.stock_id
            ).order_by(DailyPrice.date.desc()).first()
            
            if latest_price:
                print(f"최신 데이터: {latest_price.date}, 종가: {latest_price.close_price}")
            
            # 6. 특정 날짜 테스트
            test_date = date(2025, 7, 18)
            specific_price = db.query(DailyPrice).filter(
                DailyPrice.stock_id == samsung.stock_id,
                DailyPrice.date == test_date
            ).first()
            
            if specific_price:
                print(f"2025-07-18 데이터: 종가 {specific_price.close_price}")
            else:
                print("2025-07-18 데이터 없음")
        
        # 7. market_stats 테이블 확인
        market_stat_count = db.query(MarketStat).count()
        print(f"시장 통계 데이터 수: {market_stat_count}")
        
        # 8. 최신 시장 통계
        latest_stat = db.query(MarketStat).order_by(MarketStat.date.desc()).first()
        if latest_stat:
            print(f"최신 시장 통계: {latest_stat.date}, 시장: {latest_stat.market}")
            
    except Exception as e:
        print(f"오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_db_connection()