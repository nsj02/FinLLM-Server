# LLM용 금융 데이터 API 함수 가이드

## 📋 개요
이 API는 한국 주식 시장(KOSPI/KOSDAQ) 데이터를 조회할 수 있는 RESTful API입니다.
LLM이 사용자의 질문에 답하기 위해 다음 함수들을 호출할 수 있습니다.

**Base URL**: `http://localhost:8000`

## 🔍 주요 API 엔드포인트

### 1. 종목 검색
```
GET /stocks/search
```
**용도**: 종목명이나 코드로 종목을 검색합니다.
**파라미터**:
- `query`: 검색어 (종목명 또는 코드)
- `market`: 시장 (KOSPI/KOSDAQ/ALL) - 기본값: ALL
- `limit`: 조회 개수 - 기본값: 10

**예시**:
```
GET /stocks/search?query=삼성&limit=5
GET /stocks/search?query=005930&market=KOSPI
```

### 2. 특정 날짜 주식 가격 조회
```
GET /stock/price
```
**용도**: 특정 날짜의 주식 가격 정보를 조회합니다.
**파라미터**:
- `ticker`: 주식 티커 (예: 005930.KS)
- `date`: 조회 날짜 (YYYY-MM-DD)
- `price_type`: 가격 유형 (open/high/low/close/volume) - 기본값: close

**예시**:
```
GET /stock/price?ticker=005930.KS&date=2024-11-06&price_type=open
GET /stock/price?ticker=000660.KS&date=2025-05-12&price_type=close
```

### 3. 시장 통계 조회
```
GET /market/stats
```
**용도**: 특정 날짜의 시장 통계를 조회합니다.
**파라미터**:
- `date`: 조회 날짜 (YYYY-MM-DD)
- `market`: 시장 (KOSPI/KOSDAQ/ALL) - 기본값: ALL

**예시**:
```
GET /market/stats?date=2025-06-23&market=KOSPI
GET /market/stats?date=2024-12-04&market=ALL
```

### 4. 시장 지수 조회
```
GET /market/index
```
**용도**: 특정 날짜의 시장 지수를 조회합니다.
**파라미터**:
- `date`: 조회 날짜 (YYYY-MM-DD)
- `market`: 시장 (KOSPI/KOSDAQ) - 기본값: KOSPI

**예시**:
```
GET /market/index?date=2024-07-15&market=KOSPI
GET /market/index?date=2025-01-20&market=KOSDAQ
```

### 5. 시장 순위 조회
```
GET /market/rankings
```
**용도**: 특정 날짜의 시장 순위를 조회합니다.
**파라미터**:
- `date`: 조회 날짜 (YYYY-MM-DD)
- `market`: 시장 (KOSPI/KOSDAQ)
- `sort_by`: 정렬 기준 (change_rate/volume/close_price) - 기본값: change_rate
- `order`: 정렬 순서 (desc/asc) - 기본값: desc
- `limit`: 조회 개수 - 기본값: 10

**예시**:
```
GET /market/rankings?date=2025-01-20&market=KOSPI&sort_by=change_rate&order=desc&limit=5
GET /market/rankings?date=2024-10-11&market=KOSPI&sort_by=volume&order=desc&limit=10
```

## 💡 질문 유형별 API 사용 예시

### 개별 종목 가격 조회
**질문**: "동부건설우의 2024-11-06 시가는?"
**API 호출**:
1. `GET /stocks/search?query=동부건설우` - 종목 코드 찾기
2. `GET /stock/price?ticker={찾은_코드}&date=2024-11-06&price_type=open`

### 시장 통계 조회
**질문**: "2025-06-23에 상승한 종목은 몇 개인가?"
**API 호출**:
```
GET /market/stats?date=2025-06-23&market=ALL
```
응답에서 `rising_stocks` 필드 확인

### 순위 조회
**질문**: "2025-01-20에서 KOSPI에서 상승률 높은 종목 5개는?"
**API 호출**:
```
GET /market/rankings?date=2025-01-20&market=KOSPI&sort_by=change_rate&order=desc&limit=5
```

### 거래량 순위
**질문**: "2025-06-27에서 거래량 기준 상위 10개 종목은?"
**API 호출**:
```
GET /market/rankings?date=2025-06-27&market=ALL&sort_by=volume&order=desc&limit=10
```

## 🏷️ 종목 코드 형식
- **KOSPI**: 6자리 숫자 + ".KS" (예: 005930.KS)
- **KOSDAQ**: 6자리 숫자 + ".KQ" (예: 293490.KQ)

## 📊 응답 데이터 형식

### 주식 가격 응답
```json
{
    "symbol": "005930.KS",
    "name": "삼성전자",
    "date": "2024-11-06",
    "open": 58000,
    "high": 59000,
    "low": 57500,
    "close": 58500,
    "volume": 1000000,
    "change": 500,
    "change_rate": 0.86,
    "requested_value": 58000
}
```

### 시장 통계 응답
```json
{
    "date": "2025-06-23",
    "market": "ALL",
    "rising_stocks": 1500,
    "falling_stocks": 800,
    "unchanged_stocks": 50,
    "total_stocks": 2350,
    "total_volume": 1000000000,
    "total_value": 50000000000000
}
```

### 순위 응답
```json
[
    {
        "rank": 1,
        "symbol": "005930.KS",
        "name": "삼성전자",
        "market": "KOSPI",
        "open": 58000,
        "high": 59000,
        "low": 57500,
        "close": 58500,
        "volume": 1000000,
        "change": 500,
        "change_rate": 0.86
    }
]
```

## 🔧 오류 처리
- **404**: 데이터를 찾을 수 없음
- **500**: 서버 내부 오류
- **422**: 잘못된 파라미터

## 💻 실제 사용 예시

### 1. 복합 질문 처리 예시
**질문**: "현대사료의 2025-05-12 시가는?"

**단계**:
1. 종목 검색: `GET /stocks/search?query=현대사료`
2. 결과에서 티커 확인 (예: 001520.KS)
3. 가격 조회: `GET /stock/price?ticker=001520.KS&date=2025-05-12&price_type=open`

### 2. 시장 분석 예시
**질문**: "2024-12-04 KOSPI 시장에서 상승한 종목 수는?"

**단계**:
1. 시장 통계 조회: `GET /market/stats?date=2024-12-04&market=KOSPI`
2. 응답의 `rising_stocks` 값 확인

이 API들을 조합하여 복잡한 금융 데이터 질문에 답할 수 있습니다!