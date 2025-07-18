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

# ==============================================================================
# 4. 서버 실행
# ==============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)