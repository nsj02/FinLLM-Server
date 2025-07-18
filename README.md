# FinLLM-Server

FinDB 데이터베이스를 활용한 금융 데이터 API 서버입니다.

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

## 🔧 주요 엔드포인트

### 주식 데이터
- `GET /stock/history?ticker=005930.KS&days=30` - 주가 이력 조회
- `GET /stock/info?ticker=005930.KS` - 주식 정보 조회
- `GET /stock/actions?ticker=005930.KS` - 주식 활동 조회
- `GET /stock/financials?ticker=005930.KS&financial_type=income_stmt` - 재무제표 조회
- `GET /stock/holders?ticker=005930.KS&holder_type=major_holders` - 주주 정보 조회
- `GET /stock/recommendations?ticker=005930.KS` - 애널리스트 추천 조회

### 지원 종목
- 삼성전자: 005930.KS
- SK하이닉스: 000660.KS
- NAVER: 035420.KS
- 카카오: 035720.KS
- POSCO홀딩스: 005490.KS
- 카카오게임즈: 293490.KQ
- 크래프톤: 259960.KQ
- 셀트리온: 068270.KQ

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