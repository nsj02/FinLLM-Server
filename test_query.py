#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Stock, DailyPrice
from datetime import datetime

# 로컬 MySQL 연결
DB_URI = 'mysql+pymysql://root@localhost:3306/finance_db'
engine = create_engine(DB_URI)
Session = sessionmaker(bind=engine)

def test_stock_search(stock_name):
    session = Session()
    try:
        print(f"\n=== '{stock_name}' 검색 ===")
        
        # 1. 정확한 종목명 매칭
        exact_match = session.query(Stock).filter(Stock.name == stock_name, Stock.is_active == True).first()
        if exact_match:
            print(f"정확 매칭: {exact_match.name} ({exact_match.symbol})")
            return exact_match
        
        # 2. 심볼 매칭
        symbol_match = session.query(Stock).filter(Stock.symbol == stock_name, Stock.is_active == True).first()
        if symbol_match:
            print(f"심볼 매칭: {symbol_match.name} ({symbol_match.symbol})")
            return symbol_match
        
        # 3. KRX 코드 매칭
        krx_match = session.query(Stock).filter(Stock.krx_code == stock_name, Stock.is_active == True).first()
        if krx_match:
            print(f"KRX 매칭: {krx_match.name} ({krx_match.symbol})")
            return krx_match
        
        # 4. 부분 매칭
        partial_matches = session.query(Stock).filter(
            (Stock.name.contains(stock_name)) | 
            (Stock.symbol.contains(stock_name)) |
            (Stock.krx_code.contains(stock_name)),
            Stock.is_active == True
        ).limit(5).all()
        
        if partial_matches:
            print(f"부분 매칭 결과:")
            for match in partial_matches:
                print(f"  - {match.name} ({match.symbol})")
            return partial_matches[0]
        
        print("매칭 결과 없음")
        return None
        
    finally:
        session.close()

def test_price_data(stock_obj, date_str):
    session = Session()
    try:
        query_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        price_data = session.query(DailyPrice).filter(
            DailyPrice.stock_id == stock_obj.stock_id,
            DailyPrice.date == query_date
        ).first()
        
        if price_data:
            print(f"가격 데이터 존재: {price_data.close_price}원")
            return price_data
        else:
            print(f"가격 데이터 없음: {date_str}")
            return None
    finally:
        session.close()

if __name__ == "__main__":
    # 테스트 실행
    test_cases = ["금양그린파워", "282720.KQ", "282720", "삼성전자"]
    
    for test_case in test_cases:
        stock_obj = test_stock_search(test_case)
        if stock_obj:
            test_price_data(stock_obj, "2024-08-08")