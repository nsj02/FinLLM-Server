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
            "url": os.getenv("API_SERVER_URL", "http://49.50.133.71:8000"),
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

# ==============================================================================
# 4. 기능별 OpenAPI JSON 엔드포인트
# ==============================================================================

@app.get("/openapi_basic.json")
def get_basic_openapi():
    """기본 주식 조회 API만 포함하는 OpenAPI 스키마"""
    from fastapi.openapi.utils import get_openapi
    from fastapi import FastAPI
    
    # 기본 라우터만 포함하는 임시 앱 생성
    temp_app = FastAPI(
        title="기본 주식 조회 API",
        description="한국 주식시장 기본 조회 기능 (종목 정보, 가격 데이터, 검색)",
        version="1.0.0"
    )
    temp_app.include_router(basic_router, tags=["Basic"])
    
    schema = get_openapi(
        title=temp_app.title,
        version=temp_app.version,
        description=temp_app.description,
        routes=temp_app.routes,
    )
    
    schema["openapi"] = "3.0.3"
    schema["servers"] = [{"url": os.getenv("API_SERVER_URL", "http://49.50.133.71:8000")}]
    
    # examples 제거
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

@app.get("/openapi_enhanced.json")
def get_enhanced_openapi():
    """고급 기능 API만 포함하는 OpenAPI 스키마"""
    from fastapi.openapi.utils import get_openapi
    from fastapi import FastAPI
    
    temp_app = FastAPI(
        title="고급 주식 기능 API",
        description="한국 주식시장 고급 기능 (시장 데이터, 순위, 통계)",
        version="1.0.0"
    )
    temp_app.include_router(enhanced_router, tags=["Enhanced"])
    
    schema = get_openapi(
        title=temp_app.title,
        version=temp_app.version,
        description=temp_app.description,
        routes=temp_app.routes,
    )
    
    schema["openapi"] = "3.0.3"
    schema["servers"] = [{"url": os.getenv("API_SERVER_URL", "http://49.50.133.71:8000")}]
    
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

@app.get("/openapi_technical.json")
def get_technical_openapi():
    """기술적 분석 API만 포함하는 OpenAPI 스키마"""
    from fastapi.openapi.utils import get_openapi
    from fastapi import FastAPI
    
    temp_app = FastAPI(
        title="기술적 분석 API",
        description="한국 주식시장 기술적 분석 (RSI, 볼린저밴드, 골든크로스)",
        version="1.0.0"
    )
    temp_app.include_router(technical_router, tags=["Technical"])
    
    schema = get_openapi(
        title=temp_app.title,
        version=temp_app.version,
        description=temp_app.description,
        routes=temp_app.routes,
    )
    
    schema["openapi"] = "3.0.3"
    schema["servers"] = [{"url": os.getenv("API_SERVER_URL", "http://49.50.133.71:8000")}]
    
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

@app.get("/openapi_filters.json")
def get_filters_openapi():
    """필터링 API만 포함하는 OpenAPI 스키마"""
    from fastapi.openapi.utils import get_openapi
    from fastapi import FastAPI
    
    temp_app = FastAPI(
        title="주식 필터링 API",
        description="한국 주식시장 필터링 기능 (가격대, 거래량, RSI 등)",
        version="1.0.0"
    )
    temp_app.include_router(filters_router, tags=["Filters"])
    
    schema = get_openapi(
        title=temp_app.title,
        version=temp_app.version,
        description=temp_app.description,
        routes=temp_app.routes,
    )
    
    schema["openapi"] = "3.0.3"
    schema["servers"] = [{"url": os.getenv("API_SERVER_URL", "http://49.50.133.71:8000")}]
    
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

@app.get("/openapi_simple.json")
def get_simple_openapi():
    """간단 조회 API만 포함하는 OpenAPI 스키마"""
    from fastapi.openapi.utils import get_openapi
    from fastapi import FastAPI
    
    temp_app = FastAPI(
        title="간단 조회 API",
        description="한국 주식 간단 조회 (개별 종목, 시장 통계, 순위)",
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
    schema["servers"] = [{"url": os.getenv("API_SERVER_URL", "http://49.50.133.71:8000")}]
    
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
        title="조건 검색 API",
        description="한국 주식 조건 검색 (복합 조건 필터링)",
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
    schema["servers"] = [{"url": os.getenv("API_SERVER_URL", "http://49.50.133.71:8000")}]
    
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
        title="기술적 신호 API",
        description="한국 주식 기술적 신호 (RSI, 볼린저밴드, 거래량 급증 등)",
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
    schema["servers"] = [{"url": os.getenv("API_SERVER_URL", "http://49.50.133.71:8000")}]
    
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