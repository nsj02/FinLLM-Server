# server.py - 리팩토링된 API 서버 (데이터베이스 분리 버전)

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 라우터 임포트
from routes.basic import router as basic_router
from routes.enhanced import router as enhanced_router
from routes.technical import router as technical_router
from routes.filters import router as filters_router
from routes.query import router as query_router
from routes.financial import router as financial_router

# ==============================================================================
# 1. Pydantic 응답 모델(Response Models)
# ==============================================================================

class Message(BaseModel):
    message: str
    
    class Config:
        extra = 'forbid'

# ==============================================================================
# 2. FastAPI 애플리케이션 설정
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

# OpenAPI 3.0.3 스키마 설정 (ClovaStudio 호환)
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
            "url": "http://49.50.133.71:8000",
            "description": "Yahoo Finance API Server"
        }
    ]
    
    # ClovaStudio 호환성을 위해 examples 속성 제거
    def remove_examples(schema_dict):
        if isinstance(schema_dict, dict):
            # examples 속성 제거
            if 'examples' in schema_dict:
                del schema_dict['examples']
            # 중첩된 객체에서도 재귀적으로 제거
            for key, value in schema_dict.items():
                remove_examples(value)
        elif isinstance(schema_dict, list):
            for item in schema_dict:
                remove_examples(item)
    
    # 전체 스키마에서 examples 제거
    remove_examples(openapi_schema)
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# ==============================================================================
# 3. 라우터 등록
# ==============================================================================

# 기본 라우터 (루트, 헬스체크, 기본 주식 API)
app.include_router(basic_router, tags=["Basic"])

# 고급 라우터 (시장 데이터, 검색 등)
app.include_router(enhanced_router, tags=["Enhanced"])

# 기술적 지표 라우터
app.include_router(technical_router, tags=["Technical Analysis"])

# 필터링 라우터
app.include_router(filters_router, tags=["Filters"])

# 통합 쿼리 라우터 (신규)
app.include_router(query_router, tags=["Query"])

# 재무제표 분석 라우터 (신규)
app.include_router(financial_router, tags=["Financial Analysis"])

# ==============================================================================
# 4. 핵심 OpenAPI JSON 엔드포인트 (ClovaStudio 스킬셋용)
# ==============================================================================

@app.get("/openapi_simple.json")
def get_simple_openapi():
    """간단 조회 API만 포함하는 OpenAPI 스키마"""
    from fastapi.openapi.utils import get_openapi
    from fastapi import FastAPI
    
    temp_app = FastAPI(
        title="한국 주식시장 간단 조회 API",
        description="""이 API는 한국 주식시장의 기본적인 정보 조회를 위한 단일 엔드포인트를 제공합니다.

== 엔드포인트 ==
GET /query/simple

== 주요 기능별 사용법 ==

1. 개별 종목 가격 조회
질문 유형: "[종목명]의 [날짜] [가격타입]은?"
파라미터: stock={종목명}&date={날짜}&price_type={가격타입}

2. 시장 통계 조회  
질문 유형: "[날짜]에 상승한/하락한/거래된 종목은 몇 개?" 또는 "[날짜] 거래대금은?" 또는 "[날짜] 지수는?"
파라미터: date={날짜}&stat_type={통계타입}&market={시장}

3. 시장 순위 조회
질문 유형: "[날짜]에서 [시장]에서 [기준] 높은/많은 종목 [개수]개는?"
파라미터: date={날짜}&rank_type={순위기준}&market={시장}&direction={방향}&limit={개수}

== 중요 ==
- 복합조건 검색 불가 (예: "5% 이상 상승하고 거래량 많은 종목" → filters API 사용)
- 기술적 분석 불가 (예: "RSI 과매수 종목" → signal API 사용)""",
        version="1.0.0"
    )
    temp_app.include_router(query_router, tags=["Simple"])
    
    schema = get_openapi(
        title=temp_app.title,
        version=temp_app.version,
        description=temp_app.description,
        routes=[route for route in temp_app.routes if hasattr(route, 'path') and route.path == '/query/simple'],
    )
    
    schema["openapi"] = "3.0.3"
    schema["servers"] = [{"url": "http://49.50.133.71:8000"}]
    
    def remove_examples(schema_dict):
        if isinstance(schema_dict, dict):
            if 'examples' in schema_dict:
                del schema_dict['examples']
            for value in schema_dict.values():
                remove_examples(value)
        elif isinstance(schema_dict, list):
            for item in schema_dict:
                remove_examples(item)
    
    remove_examples(schema)
    return schema

@app.get("/openapi_filter.json")
def get_filter_openapi():
    """조건 검색 API만 포함하는 OpenAPI 스키마"""
    from fastapi.openapi.utils import get_openapi
    from fastapi import FastAPI
    
    temp_app = FastAPI(
        title="한국 주식 조건검색 필터 API",
        description="""한국 주식시장에서 복합 조건을 만족하는 종목을 검색합니다.

주요 기능:
- 등락률 조건 검색 (상승률/하락률 범위 설정)  
- 거래량 조건 검색 (전날대비 증가율, 절대량)
- 주가 범위 조건 검색 (최소/최대 종가)
- 시장별 필터링 (KOSPI/KOSDAQ/전체)
- 복합 조건 동시 적용 (AND 연산)

사용 예시:
1. 등락률 +5% 이상: date=2024-09-25&change_rate_min=5
2. 거래량 300% 증가: date=2024-09-25&volume_change_min=300  
3. 복합조건: date=2024-09-25&change_rate_min=5&volume_change_min=300
4. 가격범위: date=2024-09-25&price_min=50000&price_max=150000

필수: date (YYYY-MM-DD)
선택: change_rate_min/max, volume_change_min, volume_min, price_min/max, market""",
        version="1.0.0"
    )
    temp_app.include_router(query_router, tags=["Filter"])
    
    schema = get_openapi(
        title=temp_app.title,
        version=temp_app.version,
        description=temp_app.description,
        routes=[route for route in temp_app.routes if hasattr(route, 'path') and route.path == '/query/filter'],
    )
    
    schema["openapi"] = "3.0.3"
    schema["servers"] = [{"url": "http://49.50.133.71:8000"}]
    
    def remove_examples(schema_dict):
        if isinstance(schema_dict, dict):
            if 'examples' in schema_dict:
                del schema_dict['examples']
            for value in schema_dict.values():
                remove_examples(value)
        elif isinstance(schema_dict, list):
            for item in schema_dict:
                remove_examples(item)
    
    remove_examples(schema)
    return schema

@app.get("/openapi_signal.json")
def get_signal_openapi():
    """기술적 신호 API만 포함하는 OpenAPI 스키마"""
    from fastapi.openapi.utils import get_openapi
    from fastapi import FastAPI
    
    temp_app = FastAPI(
        title="한국 주식 기술적분석 신호 API",
        description="""이 API는 한국 주식시장에서 기술적 지표 기반 신호를 분석하기 위한 단일 엔드포인트를 제공합니다.

== 엔드포인트 ==
GET /query/signal

== 주요 기능 ==
기술적 지표 신호 분석
질문 유형: "[날짜]에 [기술적지표] [조건]인 종목은?"

== 지원 기술적 지표 ==
- RSI: 과매수(70이상)/과매도(30이하) 신호
- 볼린저밴드: 상단/하단 돌파 신호
- 이동평균선: 골든크로스/데드크로스 신호
- MACD: 매수/매도 신호
- 거래량: 평균대비 급증 신호
- 돌파매매: 저항선/지지선 돌파 신호

== 사용 예시 ==
- "RSI 70 이상 과매수 종목은?" → RSI 과매수 신호
- "볼린저밴드 하단 터치 종목은?" → 볼린저밴드 하단 돌파
- "거래량 평균대비 3배 급증 종목은?" → 거래량 급증 신호
- "골든크로스 발생 종목은?" → 이동평균선 골든크로스

== 중요 ==
- 단순 가격조회 불가 (예: "삼성전자 종가는?" → simple API 사용)
- 조건필터링 불가 (예: "5% 이상 상승한 종목" → filter API 사용)""",
        version="1.0.0"
    )
    temp_app.include_router(query_router, tags=["Signal"])
    
    schema = get_openapi(
        title=temp_app.title,
        version=temp_app.version,
        description=temp_app.description,
        routes=[route for route in temp_app.routes if hasattr(route, 'path') and route.path == '/query/signal'],
    )
    
    schema["openapi"] = "3.0.3"
    schema["servers"] = [{"url": "http://49.50.133.71:8000"}]
    
    def remove_examples(schema_dict):
        if isinstance(schema_dict, dict):
            if 'examples' in schema_dict:
                del schema_dict['examples']
            for value in schema_dict.values():
                remove_examples(value)
        elif isinstance(schema_dict, list):
            for item in schema_dict:
                remove_examples(item)
    
    remove_examples(schema)
    return schema

@app.get("/openapi_financial.json")
def get_financial_openapi():
    """재무분석 API만 포함하는 OpenAPI 스키마"""
    from fastapi.openapi.utils import get_openapi
    from fastapi import FastAPI
    
    temp_app = FastAPI(
        title="한국 기업 재무분석 API",
        description="""한국 상장기업의 재무제표를 분석하는 API입니다.

주요 기능:
- 한국 상장기업 재무제표 데이터 수집 (DART 전자공시시스템 연동)
- 전문 증권분석사 관점의 투자보고서 작성 지침 제공
- Stock 테이블 기반 정확한 기업명 매칭
- 최근 3년간 재무데이터 종합 분석

사용법:
회사명을 입력하면 해당 기업의 재무데이터와 전문 분석 지침을 반환합니다.

지원 기업: 한국 거래소(KRX) 상장 전 종목
분석 항목: 매출 성장률, 수익성, 재무 안정성, 투자 위험도, 투자 등급

예시: company=삼성전자, company=SK하이닉스, company=네이버""",
        version="1.0.0"
    )
    temp_app.include_router(financial_router, tags=["Financial"])
    
    schema = get_openapi(
        title=temp_app.title,
        version=temp_app.version,
        description=temp_app.description,
        routes=[route for route in temp_app.routes if hasattr(route, 'path') and route.path == '/financial/report'],
    )
    
    schema["openapi"] = "3.0.3"
    schema["servers"] = [{"url": "http://49.50.133.71:8000"}]
    
    def remove_examples(schema_dict):
        if isinstance(schema_dict, dict):
            if 'examples' in schema_dict:
                del schema_dict['examples']
            for value in schema_dict.values():
                remove_examples(value)
        elif isinstance(schema_dict, list):
            for item in schema_dict:
                remove_examples(item)
    
    remove_examples(schema)
    return schema

# ==============================================================================
# 5. 서버 실행
# ==============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)