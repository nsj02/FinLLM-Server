# FinLLM-Server

한국 주식시장 전문 API 서버 (2,757개 종목 지원)

FinDB 데이터베이스를 활용한 실시간 금융 데이터 API 서버입니다.

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 의존성 설치
pip install -r requirements.txt
```

### 2. 데이터베이스 연결

FinDB 프로젝트의 TimescaleDB가 실행되어 있어야 합니다:

```bash
# FinDB 디렉토리에서 실행
cd ../FinDB
docker-compose up -d
```

### 3. API 서버 실행

```bash
# 로컬 실행
python server.py

# 또는 Docker로 실행
docker-compose up -d
```

## 📚 API 문서

서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🤖 ClovaStudio 스킬셋 연동

네이버 ClovaStudio와 연동을 위한 기능별 OpenAPI 스키마를 제공합니다:

### 기능별 OpenAPI JSON 엔드포인트
- `/openapi_basic.json` - 기본 주식 조회 (종목 정보, 가격 데이터, 검색)
- `/openapi_enhanced.json` - 고급 기능 (시장 데이터, 순위, 통계)
- `/openapi_technical.json` - 기술적 분석 (RSI, 볼린저밴드, 골든크로스)
- `/openapi_filters.json` - 필터링 (가격대, 거래량, RSI 등)

### ClovaStudio 스킬셋 등록 방법
1. 각 기능별 OpenAPI JSON URL을 스킬셋 등록 시 사용
2. 예시: `http://49.50.133.71:8000/openapi_basic.json`
3. 토큰 수 최적화를 위해 examples 속성 제거됨

## 🔧 주요 기능

### 1. 기본 주식 조회 (Basic)
- 개별 종목 정보 조회
- 종목 검색
- 가격 히스토리

### 2. 고급 기능 (Enhanced)  
- 시장 통계
- 종목 순위
- 거래량 분석

### 3. 기술적 분석 (Technical)
- RSI, 볼린저밴드, MACD
- 골든크로스/데드크로스 시그널
- 매매 신호

### 4. 필터링 (Filters)
- 가격대별 필터링
- 거래량 조건 필터링
- 기술적 지표 조건 필터링

### 지원 종목 (2,757개)
- **KOSPI**: 삼성전자(005930.KS), SK하이닉스(000660.KS), NAVER(035420.KS) 등
- **KOSDAQ**: 카카오게임즈(293490.KQ), 크래프톤(259960.KQ), 셀트리온(068270.KQ) 등

## 🏗️ 기술 스택

- **Framework**: FastAPI
- **Database**: TimescaleDB (FinDB 연결)
- **ORM**: SQLAlchemy
- **Container**: Docker
- **Language**: Python 3.11

## 🔄 환경변수

| 변수명 | 기본값 | 설명 |
|--------|--------|------|
| `DATABASE_URL` | `postgresql://postgres:password@localhost:5432/finance_db` | 데이터베이스 연결 URL |
| `API_SERVER_URL` | `http://localhost:8000` | API 서버 URL |

## 🐳 Docker 사용법

```bash
# 전체 시스템 실행 (FinDB + API 서버)
docker-compose up -d

# API 서버만 실행 (FinDB가 별도로 실행 중인 경우)
docker-compose up -d api-server
```

## 📈 연동 프로젝트

- [FinDB](../FinDB) - TimescaleDB 기반 금융 데이터베이스