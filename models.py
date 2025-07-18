# models.py - Database models for FinLLM-Server
import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey, Boolean, Text, DateTime, Index, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func

# 데이터베이스 연결 설정
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/finance_db')
engine = create_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20)
Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Stock(Base):
    __tablename__ = 'stocks'
    
    stock_id = Column(Integer, primary_key=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    krx_code = Column(String(20), index=True)
    name = Column(String(100), nullable=False, index=True)
    market = Column(String(20), index=True)
    sector = Column(String(100), index=True)
    industry = Column(String(100))
    listing_date = Column(Date)
    delisting_date = Column(Date)
    is_active = Column(Boolean, default=True)
    description = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 관계 설정
    daily_prices = relationship("DailyPrice", back_populates="stock")
    technical_indicators = relationship("TechnicalIndicator", back_populates="stock")

class DailyPrice(Base):
    __tablename__ = 'daily_prices'
    
    stock_id = Column(Integer, ForeignKey('stocks.stock_id', ondelete='CASCADE'), primary_key=True)
    date = Column(Date, nullable=False, primary_key=True)
    open_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    close_price = Column(Float)
    adjusted_close = Column(Float)
    volume = Column(Integer)
    change = Column(Float)
    change_rate = Column(Float)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 관계 설정
    stock = relationship("Stock", back_populates="daily_prices")
    
    # 인덱스 추가
    __table_args__ = (
        Index('ix_daily_prices_date', 'date'),
        Index('ix_daily_prices_stock_id', 'stock_id'),
    )

class TechnicalIndicator(Base):
    __tablename__ = 'technical_indicators'
    
    stock_id = Column(Integer, ForeignKey('stocks.stock_id', ondelete='CASCADE'), primary_key=True)
    date = Column(Date, nullable=False, primary_key=True)
    
    # 이동평균선
    ma5 = Column(Float)
    ma10 = Column(Float)
    ma20 = Column(Float)
    ma60 = Column(Float)
    ma120 = Column(Float)
    
    # 볼린저 밴드
    bb_upper = Column(Float)
    bb_middle = Column(Float)
    bb_lower = Column(Float)
    bb_width = Column(Float)
    
    # RSI
    rsi = Column(Float)
    
    # MACD
    macd = Column(Float)
    macd_signal = Column(Float)
    macd_hist = Column(Float)
    
    # 볼륨 관련
    volume_ma20 = Column(Float)
    volume_ratio = Column(Float)
    
    # 캔들 패턴
    is_doji = Column(Boolean)
    is_hammer = Column(Boolean)
    
    # 시그널
    golden_cross = Column(Boolean)
    death_cross = Column(Boolean)
    bb_upper_touch = Column(Boolean)
    bb_lower_touch = Column(Boolean)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 관계 설정
    stock = relationship("Stock", back_populates="technical_indicators")
    
    # 인덱스 추가
    __table_args__ = (
        Index('ix_tech_indicators_date', 'date'),
        Index('ix_tech_indicators_stock_id', 'stock_id'),
        Index('ix_tech_indicators_rsi', 'rsi'),
        Index('ix_tech_indicators_volume_ratio', 'volume_ratio'),
    )

class MarketIndex(Base):
    __tablename__ = 'market_indices'
    
    market = Column(String(20), nullable=False, primary_key=True)
    date = Column(Date, nullable=False, primary_key=True)
    open_index = Column(Float)
    high_index = Column(Float)
    low_index = Column(Float)
    close_index = Column(Float)
    volume = Column(Integer)
    change = Column(Float)
    change_rate = Column(Float)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 인덱스 추가
    __table_args__ = (
        Index('ix_market_indices_date', 'date'),
        Index('ix_market_indices_market', 'market'),
    )

class MarketStat(Base):
    __tablename__ = 'market_stats'
    
    market = Column(String(20), nullable=False, primary_key=True)
    date = Column(Date, nullable=False, primary_key=True)
    rising_stocks = Column(Integer)
    falling_stocks = Column(Integer)
    unchanged_stocks = Column(Integer)
    total_stocks = Column(Integer)
    total_volume = Column(BigInteger)
    total_value = Column(Float)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 인덱스 추가
    __table_args__ = (
        Index('ix_market_stats_date', 'date'),
        Index('ix_market_stats_market', 'market'),
    )

def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()