# routes/financial.py - 재무제표 데이터 조회 라우터
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session as SQLSession
from typing import Dict, List, Any
from datetime import datetime
import os
import httpx
import logging
from dotenv import load_dotenv

from models import get_db, Stock
from utils.helpers import common_responses, parse_date

# 환경변수 로드
load_dotenv(".env.production", encoding='utf-8')

logger = logging.getLogger(__name__)
router = APIRouter()

# DART API 키
DART_API_KEY = os.getenv("DART_API_KEY")

# HTTP 클라이언트
http_client = httpx.AsyncClient(timeout=60.0)

async def get_financial_report(company_name: str, db) -> Dict[str, Any]:
    """기업명으로 재무보고서 전체 데이터 수집 - Stock 테이블 활용"""
    
    # 1. Stock 테이블에서 회사명으로 검색 (기존 enhanced.py 로직 활용)
    try:
        # 정확한 매칭 시도
        stock = db.query(Stock).filter(
            Stock.name.contains(company_name),
            Stock.is_active == True
        ).first()
        
        # 부분 매칭 시도 (심볼, krx_code 포함)
        if not stock:
            stock = db.query(Stock).filter(
                (Stock.name.contains(company_name)) | 
                (Stock.symbol.contains(company_name)) |
                (Stock.krx_code.contains(company_name)),
                Stock.is_active == True
            ).first()
        
        if not stock:
            # 검색 결과 없으면 기본 데이터
            return {
                "company": company_name,
                "corp_code": "UNKNOWN",
                "stock_info": {"error": f"'{company_name}' 종목을 찾을 수 없습니다"},
                "financial_data": [],
                "analysis_instruction": f"{company_name} 재무분석 - 종목 정보 없음"
            }
        
        # 2. 찾은 Stock 정보
        stock_info = {
            "name": stock.name,
            "symbol": stock.symbol,
            "krx_code": stock.krx_code,
            "market": stock.market,
            "sector": stock.sector,
            "industry": stock.industry
        }
        
        # 3. DART 기업코드 (krx_code를 8자리 형태로 변환)
        corp_code = stock.krx_code.zfill(8) if stock.krx_code else "00000000"
        
        # 4. 최근 3년 DART 재무데이터 수집
        current_year = datetime.now().year
        years = [str(current_year - i) for i in range(3, 0, -1)]
        all_financial_data = []
        
        for year in years:
            if not DART_API_KEY:
                # 테스트 데이터
                test_data = {
                    "year": year,
                    "company": stock.name,
                    "revenue": f"{stock.name} {year}년 매출액: 100조원",
                    "operating_profit": f"{stock.name} {year}년 영업이익: 15조원",
                    "net_profit": f"{stock.name} {year}년 당기순이익: 12조원",
                    "total_assets": f"{stock.name} {year}년 총자산: 500조원",
                    "note": "테스트 데이터 - DART API 키 필요"
                }
                all_financial_data.append(test_data)
                continue
            
            # 5. 실제 DART API 호출
            try:
                url = f"https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json?crtfc_key={DART_API_KEY}&corp_code={corp_code}&bsns_year={year}&reprt_code=11011&fs_div=OFS"
                
                async with http_client as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        data = response.json()
                        if "list" in data and data["list"]:
                            # 주요 재무지표 추출
                            year_data = {"year": year, "company": stock.name, "accounts": []}
                            
                            # 주요 계정과목만 추출 (매출액, 영업이익, 당기순이익, 자산총계, 부채총계)
                            key_accounts = ["매출액", "영업이익", "당기순이익", "자산총계", "부채총계", "자본총계"]
                            
                            for item in data["list"]:
                                account_name = item.get("account_nm", "")
                                if any(key in account_name for key in key_accounts):
                                    account_info = {
                                        "account_name": account_name,
                                        "amount": item.get("thstrm_amount", "0"),
                                        "currency": "KRW"
                                    }
                                    year_data["accounts"].append(account_info)
                            
                            all_financial_data.append(year_data)
                        else:
                            # 데이터 없음
                            all_financial_data.append({
                                "year": year,
                                "company": stock.name,
                                "note": f"{year}년 DART 데이터 없음"
                            })
                    else:
                        all_financial_data.append({
                            "year": year,
                            "company": stock.name,
                            "error": f"DART API 오류: {response.status_code}"
                        })
            except Exception as e:
                logger.error(f"{year}년도 DART 데이터 조회 오류: {str(e)}")
                all_financial_data.append({
                    "year": year,
                    "company": stock.name,
                    "error": f"데이터 조회 실패: {str(e)}"
                })
        
        # 6. 분석 지침 생성 (실제 분석을 강제하는 명확한 프롬프트)
        analysis_instruction = f"""
        {stock.name}의 재무제표를 바탕으로 전문 투자보고서를 작성해주세요.

        == 기업 정보 ==
        - 회사명: {stock.name}
        - 종목코드: {stock.symbol}
        - 시장: {stock.market}
        - 업종: {stock.sector}
        - 세부업종: {stock.industry}

        == 제공된 재무데이터 ==
        위에 제공된 최근 3년간의 DART 재무데이터를 반드시 활용하여 다음을 분석해주세요:

        **1. 매출 성장성 분석 (필수)**
        - 최근 3년간 매출액 수치를 구체적으로 제시하고 연평균 성장률 계산
        - 매출 증감의 주요 원인 분석
        - 향후 매출 전망

        **2. 수익성 분석 (필수)**
        - 영업이익과 영업이익률 3년 추이 분석
        - 당기순이익과 순이익률 변화 분석
        - 수익성 개선/악화 요인 진단

        **3. 재무 안정성 분석 (필수)**
        - 총자산, 부채총계, 자본총계 현황 분석
        - 부채비율 = (부채총계/자본총계) × 100 계산
        - 자기자본비율 = (자본총계/총자산) × 100 계산
        - 재무구조 건전성 평가

        **4. 종합 투자 평가 (필수)**
        - 사업 리스크 요인
        - 재무 리스크 평가
        - 최종 투자 등급: A(매수)/B(보유)/C(관망)/D(매도) 중 선택
        - 등급 선정 근거를 구체적 수치로 설명

        **5. 투자 조언 (필수)**
        - 목표주가 또는 적정 밸류에이션 제시
        - 투자시 주의사항
        - 모니터링 포인트

        ⚠️ 주의: 반드시 제공된 재무데이터의 구체적 수치를 인용하여 분석하고, 단순한 일반론이 아닌 {stock.name}만의 특징을 분석해주세요.
        ⚠️ 각 항목별로 구체적인 수치와 비율을 계산하여 제시해주세요.
        """
        
        return {
            "company": stock.name,
            "corp_code": corp_code,
            "stock_info": stock_info,
            "period": f"{years[0]}-{years[-1]}",
            "financial_data": all_financial_data,
            "analysis_instruction": analysis_instruction
        }
        
    except Exception as e:
        logger.error(f"재무보고서 생성 중 오류: {str(e)}")
        return {
            "company": company_name,
            "error": f"시스템 오류: {str(e)}",
            "analysis_instruction": f"{company_name} 분석 중 시스템 오류 발생"
        }


@router.get("/financial/report", summary="기업 재무보고서 작성")
async def create_financial_report(
    company: str = Query(..., description="회사명", examples=["삼성전자"]),
    db: SQLSession = Depends(get_db)
):
    """HyperCLOVA 스킬셋용 - 기업 재무보고서 데이터 제공"""
    try:
        # Stock 테이블을 활용한 재무보고서 데이터 수집
        report_data = await get_financial_report(company, db)
        
        # 결과 반환
        result = {
            "query_type": "financial_report",
            "company": report_data.get("company", company),
            "report_data": report_data,
            "query_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 성공적으로 데이터를 찾은 경우
        if "error" not in report_data:
            result["formatted_answer"] = f"{report_data['company']} 재무보고서 데이터 수집 완료 - HyperCLOVA가 전문 투자보고서를 작성합니다"
        else:
            result["formatted_answer"] = f"{company} 검색 실패 - 종목 정보를 확인해주세요"
        
        return result
        
    except Exception as e:
        logger.error(f"재무보고서 작성 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"보고서 작성 중 오류: {str(e)}")

@router.get("/financial/health", summary="재무분석 서비스 상태")
async def financial_health():
    """재무분석 서비스 상태 확인"""
    return {
        "status": "active",
        "data_source": "DART 전자공시시스템",
        "dart_api": "active" if DART_API_KEY else "test_mode",
        "service": "기업 재무보고서 데이터 제공",
        "description": "HyperCLOVA 스킬셋에서 호출하여 DART 재무데이터 + 분석지침 반환"
    }