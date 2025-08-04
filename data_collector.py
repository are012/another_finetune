# 필요한 라이브러리 설치
# !pip install requests beautifulsoup4

import requests
from bs4 import BeautifulSoup # HTML 태그를 제거하기 위해 사용
from typing import List, Dict
import xml.etree.ElementTree as ET
import pandas as pd
import os
from datetime import datetime, timedelta
import json

def fetch_naver_news(company_name: str, display_count: int = 5) -> List[Dict[str, str]]:
    """
    네이버 검색 API를 호출하여 특정 회사의 최신 뉴스를 가져옵니다.
    
    Args:
        company_name (str): 검색할 회사 이름.
        display_count (int): 가져올 뉴스 기사 수 (기본값: 5).

    Returns:
        list[dict]: 뉴스 기사 딕셔너리 리스트 (각 딕셔너리는 'title', 'description' 키를 포함).
    """
    # 1. 네이버 개발자 센터에서 발급받은 Client ID와 Client Secret
    NAVER_CLIENT_ID = "" # ◀◀◀ 본인의 Client ID로 교체
    NAVER_CLIENT_SECRET = "" # ◀◀◀ 본인의 Client Secret으로 교체
    
    # 네이버 뉴스 검색 API 엔드포인트
    URL = "https://openapi.naver.com/v1/search/news.json"

    # 2. 검색어 구체화
    # 회사 이름만으로 검색하여 더 많은 뉴스를 가져오도록 합니다.
    # 너무 구체적인 키워드는 결과 수를 제한할 수 있습니다.
    query = f'{company_name}'
    
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    
    params = {
        "query": query,
        "display": display_count,
        "start": 1,  # 검색 시작 위치
        "sort": "date",  # 최신순으로 정렬
    }
    
    try:
        response = requests.get(URL, headers=headers, params=params)
        # HTTP 오류가 발생하면 예외를 발생시킵니다.
        response.raise_for_status()
        
        data = response.json()
        articles = []
        
        print(f"🔍 API 응답 정보: 총 {data.get('total', 0)}건 중 {len(data.get('items', []))}건 반환")
        
        # 3. 제목과 요약을 함께 추출하고, HTML 태그 제거
        for item in data.get('items', []):
            # BeautifulSoup을 사용해 제목에서 <b>, </b>, &quot; 등 HTML 태그 제거
            raw_title = item.get('title', '')
            cleaned_title = BeautifulSoup(raw_title, "html.parser").get_text()
            
            # 요약 내용(description)에서도 HTML 태그 제거
            raw_desc = item.get('description', '')
            cleaned_desc = BeautifulSoup(raw_desc, "html.parser").get_text()
            
            articles.append({"title": cleaned_title, "description": cleaned_desc})
        
        print(f"✅ 네이버 뉴스 API 호출 성공: '{company_name}' 관련 뉴스 {len(articles)}건 수집")
        return articles

    # 4. 에러 처리
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP 에러 발생: {http_err} - 응답 메시지: {response.text}")
        if response.status_code == 401:
            print(">> 인증 오류: Client ID와 Secret이 올바른지 확인하세요.")
        elif response.status_code == 429:
            print(">> API 호출 한도 초과: 잠시 후 다시 시도하세요.")
    except Exception as e:
        print(f"알 수 없는 오류 발생: {e}")
        
    return []

def load_corp_codes(xml_path='CORPCODE.xml'):
    """
    CORPCODE.xml 파일을 파싱하여 모든 회사명과 고유번호를
    pandas DataFrame으로 변환합니다.

    Args:
        xml_path (str): CORPCODE.xml 파일의 경로.

    Returns:
        pandas.DataFrame: 'corp_name'과 'corp_code' 컬럼을 가진 DataFrame.
                          파일을 찾지 못하면 None을 반환합니다.
    """
    try:
        # XML 파일 파싱
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        corp_list = []
        # XML의 'list' 태그를 모두 찾아서 반복합니다.
        for corp in root.findall('list'):
            # 각 태그에서 텍스트 값을 추출합니다.
            corp_name = corp.find('corp_name').text
            corp_code = corp.find('corp_code').text
            
            # 리스트에 딕셔너리 형태로 추가
            corp_list.append({
                'corp_name': corp_name,
                'corp_code': corp_code
            })
            
        # 리스트를 pandas DataFrame으로 변환
        df = pd.DataFrame(corp_list)
        print(f"✅ 총 {len(df)}개의 상장 기업 정보를 성공적으로 불러왔습니다.")
        return df

    except FileNotFoundError:
        print(f"오류: '{xml_path}' 파일을 찾을 수 없습니다. 스크립트와 같은 폴더에 있는지 확인하세요.")
        return None
    except Exception as e:
        print(f"XML 파싱 중 오류 발생: {e}")
        return None


def find_corp_code(company_name, corp_code_df):
    """
    DataFrame에서 회사명으로 고유번호를 찾습니다.

    Args:
        company_name (str): 찾고 싶은 회사의 정확한 전체 이름.
        corp_code_df (pandas.DataFrame): load_corp_codes 함수로 생성된 DataFrame.

    Returns:
        str | None: 회사의 8자리 고유번호 또는 찾지 못했을 경우 None.
    """
    if corp_code_df is None:
        return None
        
    # 'corp_name' 컬럼에서 정확히 일치하는 회사를 찾습니다.
    result = corp_code_df[corp_code_df['corp_name'] == company_name]
    
    if not result.empty:
        # 찾은 경우, 첫 번째 결과의 'corp_code' 값을 반환합니다.
        return result.iloc[0]['corp_code']
    else:
        print(f"'{company_name}'에 해당하는 회사를 찾을 수 없습니다.")
        return None


def load_corp_codes_optimized(xml_path='CORPCODE.xml', csv_path='corp_codes.csv', force_refresh=False):
    """
    CORPCODE.xml 파일을 파싱하여 CSV로 캐싱하고, 다음부터는 CSV를 읽어서 빠르게 로드합니다.
    
    Args:
        xml_path (str): CORPCODE.xml 파일의 경로 (기본값: 'CORPCODE.xml').
        csv_path (str): 캐시용 CSV 파일의 경로 (기본값: 'corp_codes.csv').
        force_refresh (bool): True면 기존 CSV를 무시하고 XML을 다시 파싱 (기본값: False).
    
    Returns:
        pandas.DataFrame: 'corp_name'과 'corp_code' 컬럼을 가진 DataFrame.
    """
    
    # 1. force_refresh가 False이고 CSV 파일이 존재하면 CSV에서 바로 로드
    if not force_refresh and os.path.exists(csv_path):
        try:
            print(f"⚡ 기존 CSV 파일에서 빠르게 로드합니다: {csv_path}")
            start_time = datetime.now()
            
            df = pd.read_csv(csv_path)
            
            end_time = datetime.now()
            load_time = (end_time - start_time).total_seconds()
            
            print(f"✅ CSV 로드 완료: {len(df)}개 기업 정보 ({load_time:.2f}초)")
            return df
            
        except Exception as e:
            print(f"⚠️ CSV 파일 읽기 실패: {e}")
            print("XML 파일에서 다시 파싱합니다...")
    
    # 2. XML 파일이 존재하지 않으면 오류 반환
    if not os.path.exists(xml_path):
        print(f"❌ '{xml_path}' 파일을 찾을 수 없습니다.")
        return None
    
    # 3. XML 파싱 (시간이 오래 걸림)
    try:
        print(f"🔄 XML 파싱 시작: {xml_path} (시간이 걸릴 수 있습니다...)")
        start_time = datetime.now()
        
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        corp_list = []
        total_corps = len(root.findall('list'))
        
        for i, corp in enumerate(root.findall('list'), 1):
            corp_name = corp.find('corp_name').text
            corp_code = corp.find('corp_code').text
            
            corp_list.append({
                'corp_name': corp_name,
                'corp_code': corp_code
            })
            
            # 진행 상황 표시 (10000개마다)
            if i % 10000 == 0:
                print(f"  파싱 진행: {i:,}/{total_corps:,} ({i/total_corps*100:.1f}%)")
        
        df = pd.DataFrame(corp_list)
        
        end_time = datetime.now()
        parse_time = (end_time - start_time).total_seconds()
        
        print(f"✅ XML 파싱 완료: {len(df)}개 기업 정보 ({parse_time:.2f}초)")
        
        # 4. CSV로 저장 (다음번에 빠르게 로드하기 위해)
        try:
            print(f"💾 CSV 파일로 저장합니다: {csv_path}")
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')  # BOM 추가로 한글 호환성 향상
            print(f"✅ CSV 저장 완료. 다음부터는 빠르게 로드됩니다!")
        except Exception as e:
            print(f"⚠️ CSV 저장 실패: {e} (기능은 정상 작동합니다)")
        
        return df
        
    except Exception as e:
        print(f"❌ XML 파싱 중 오류 발생: {e}")
        return None


def get_corp_info_fast(company_name, csv_path='corp_codes.csv'):
    """
    빠른 회사 정보 조회 함수. CSV 파일에서 바로 회사 정보를 찾습니다.
    
    Args:
        company_name (str): 찾고 싶은 회사명.
        csv_path (str): CSV 파일 경로.
        
    Returns:
        dict | None: {'corp_name': 회사명, 'corp_code': 고유번호} 또는 None.
    """
    if not os.path.exists(csv_path):
        print(f"❌ CSV 파일이 없습니다: {csv_path}")
        print("먼저 load_corp_codes_optimized() 함수를 실행해주세요.")
        return None
    
    try:
        # CSV에서 특정 회사만 검색 (메모리 효율적)
        # corp_code를 문자열로 읽어서 앞의 0이 제거되지 않도록 함
        df = pd.read_csv(csv_path, dtype={'corp_code': str})
        result = df[df['corp_name'] == company_name]
        
        if not result.empty:
            corp_code = result.iloc[0]['corp_code']
            # 8자리 형식으로 보장 (DART API 요구사항)
            corp_code = str(corp_code).zfill(8)
            return {
                'corp_name': result.iloc[0]['corp_name'],
                'corp_code': corp_code
            }
        else:
            return None
            
    except Exception as e:
        print(f"❌ 검색 중 오류: {e}")
        return None


def search_companies_by_keyword(keyword, csv_path='corp_codes.csv', max_results=20):
    """
    키워드로 회사를 검색합니다.
    
    Args:
        keyword (str): 검색할 키워드.
        csv_path (str): CSV 파일 경로.
        max_results (int): 최대 결과 개수.
        
    Returns:
        pandas.DataFrame: 검색 결과 DataFrame.
    """
    if not os.path.exists(csv_path):
        print(f"❌ CSV 파일이 없습니다: {csv_path}")
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(csv_path)
        results = df[df['corp_name'].str.contains(keyword, na=False)]
        
        if len(results) > max_results:
            print(f"🔍 '{keyword}' 검색결과: {len(results)}개 (상위 {max_results}개만 표시)")
            return results.head(max_results)
        else:
            print(f"🔍 '{keyword}' 검색결과: {len(results)}개")
            return results
            
    except Exception as e:
        print(f"❌ 검색 중 오류: {e}")
        return pd.DataFrame()


def fetch_dart_disclosures(corp_code, start_date=None, end_date=None, page_no=1, page_count=10):
    """
    DART API를 사용하여 특정 회사의 공시 정보를 가져옵니다.
    
    Args:
        corp_code (str): 8자리 회사 고유번호.
        start_date (str): 검색 시작일 (YYYYMMDD 형식, 기본값: 30일 전).
        end_date (str): 검색 종료일 (YYYYMMDD 형식, 기본값: 오늘).
        page_no (int): 페이지 번호 (기본값: 1).
        page_count (int): 페이지당 건수 (기본값: 10, 최대 100).
        
    Returns:
        List[Dict]: 공시 정보 리스트 또는 빈 리스트.
    """
    
    # DART API 키 (무료 API 키 발급 필요: https://opendart.fss.or.kr/)
    DART_API_KEY = ""  # ◀◀◀ 실제 API 키로 교체 필요!
    
    # 고유번호를 8자리 형식으로 보장
    corp_code = str(corp_code).zfill(8)
    
    # 기본 날짜 설정 (30일 전부터 오늘까지)
    if not end_date:
        end_date = datetime.now().strftime('%Y%m%d')
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
    
    # DART API 엔드포인트
    url = "https://opendart.fss.or.kr/api/list.json"
    
    params = {
        'crtfc_key': DART_API_KEY,
        'corp_code': corp_code,
        'bgn_de': start_date,
        'end_de': end_date,
        'page_no': page_no,
        'page_count': min(page_count, 100)  # 최대 100건으로 제한
    }
    
    try:
        print(f"🔍 DART API 호출: {corp_code} ({start_date}~{end_date})")
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        # API 응답 상태 확인
        if data.get('status') != '000':
            error_message = data.get('message', '알 수 없는 오류')
            print(f"❌ DART API 오류: {error_message}")
            return []
        
        # 공시 목록 추출
        disclosures = data.get('list', [])
        
        if disclosures:
            print(f"✅ DART 공시 정보 {len(disclosures)}건 수집 완료")
            
            # 필요한 정보만 추출하여 정리
            cleaned_disclosures = []
            for item in disclosures:
                cleaned_item = {
                    'corp_name': item.get('corp_name', ''),
                    'report_nm': item.get('report_nm', ''),  # 보고서명
                    'rcept_no': item.get('rcept_no', ''),    # 접수번호
                    'flr_nm': item.get('flr_nm', ''),        # 공시제출인명
                    'rcept_dt': item.get('rcept_dt', ''),    # 접수일자
                    'rm': item.get('rm', '')                 # 비고
                }
                cleaned_disclosures.append(cleaned_item)
            
            return cleaned_disclosures
        else:
            print(f"📭 해당 기간에 공시 정보가 없습니다.")
            return []
            
    except requests.exceptions.RequestException as e:
        print(f"❌ DART API 호출 실패: {e}")
        return []
    except Exception as e:
        print(f"❌ 공시 정보 처리 중 오류: {e}")
        return []


def get_company_disclosures_by_name(company_name, csv_path='corp_codes.csv', days_back=30, max_count=10):
    """
    회사명으로 최근 공시 정보를 가져오는 통합 함수.
    
    Args:
        company_name (str): 회사명.
        csv_path (str): CSV 파일 경로.
        days_back (int): 조회할 과거 일수 (기본값: 30일).
        max_count (int): 최대 공시 건수 (기본값: 10건).
        
    Returns:
        List[Dict]: 공시 정보 리스트.
    """
    
    print(f"=== {company_name} 공시 정보 조회 ===")
    
    # 1단계: 회사명으로 고유번호 찾기
    corp_info = get_corp_info_fast(company_name, csv_path)
    
    if not corp_info:
        print(f"❌ '{company_name}' 회사를 찾을 수 없습니다.")
        return []
    
    corp_code = corp_info['corp_code']
    print(f"✅ 회사 정보: {corp_info['corp_name']} ({corp_code})")
    
    # 2단계: DART API로 공시 정보 가져오기
    start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y%m%d')
    end_date = datetime.now().strftime('%Y%m%d')
    
    disclosures = fetch_dart_disclosures(
        corp_code=corp_code,
        start_date=start_date,
        end_date=end_date,
        page_count=max_count
    )
    
    return disclosures


def format_disclosures_for_llm(disclosures, company_name):
    """
    공시 정보를 LLM이 분석하기 좋은 형태로 포맷팅합니다.
    
    Args:
        disclosures (List[Dict]): 공시 정보 리스트.
        company_name (str): 회사명.
        
    Returns:
        str: 포맷팅된 공시 정보 텍스트.
    """
    
    if not disclosures:
        return f"### {company_name} 최근 공시 정보\n- 최근 30일간 공시된 정보가 없습니다."
    
    formatted_text = f"### {company_name} 최근 공시 정보\n"
    
    for i, disclosure in enumerate(disclosures, 1):
        # 날짜 포맷팅 (YYYYMMDD -> YYYY-MM-DD)
        rcept_dt = disclosure.get('rcept_dt', '')
        if len(rcept_dt) == 8:
            formatted_date = f"{rcept_dt[:4]}-{rcept_dt[4:6]}-{rcept_dt[6:8]}"
        else:
            formatted_date = rcept_dt
        
        report_nm = disclosure.get('report_nm', '제목 없음')
        flr_nm = disclosure.get('flr_nm', '제출인 미상')
        rm = disclosure.get('rm', '')
        
        formatted_text += f"\n**{i}. {report_nm}**\n"
        formatted_text += f"   - 제출일: {formatted_date}\n"
        formatted_text += f"   - 제출인: {flr_nm}\n"
        
        if rm:
            formatted_text += f"   - 비고: {rm}\n"
    
    return formatted_text


def get_important_disclosures_by_priority(company_name, csv_path='corp_codes.csv', days_back=90):
    """
    중요도별로 분류된 공시 정보를 가져오는 함수.
    
    Args:
        company_name (str): 회사명.
        csv_path (str): CSV 파일 경로.
        days_back (int): 조회할 과거 일수 (기본값: 90일).
        
    Returns:
        dict: 중요도별로 분류된 공시 정보.
    """
    
    print(f"=== {company_name} 중요 공시 정보 분석 ===")
    
    # 1. 전체 공시 가져오기 (더 많은 데이터를 위해 90일, 최대 100건)
    all_disclosures = get_company_disclosures_by_name(
        company_name, csv_path, days_back=days_back, max_count=100
    )
    
    if not all_disclosures:
        return {
            'priority_1': [], 'priority_2': [], 'priority_3': [], 'risk_signals': []
        }
    
    # 2. 중요도별 키워드 정의
    keywords = {
        'priority_1': {
            '정기보고서': ['사업보고서', '분기보고서', '반기보고서'],
            '실적공시': ['영업실적', '잠정실적', '연결실적', '별도실적']
        },
        'priority_2': {
            'M&A_투자': ['타법인주식', '타법인 주식', '출자증권', '지분취득', '지분처분'],
            '증자': ['유상증자', '무상증자', '신주발행'],
            '자사주': ['자기주식취득', '자기주식처분', '자사주매입']
        },
        'priority_3': {
            '계약수주': ['단일판매', '공급계약', '계약체결', '수주'],
            '투자확장': ['신규시설투자', '설비투자', '투자결정']
        },
        'risk_signals': {
            '지배구조': ['최대주주변경', '주주변경'],
            '법적리스크': ['소송제기', '소송신청', '분쟁']
        }
    }
    
    # 3. 공시를 중요도별로 분류
    classified_disclosures = {
        'priority_1': [],
        'priority_2': [],
        'priority_3': [],
        'risk_signals': []
    }
    
    for disclosure in all_disclosures:
        report_name = disclosure.get('report_nm', '').lower()
        classified = False
        
        # 각 우선순위별로 키워드 매칭
        for priority, categories in keywords.items():
            if classified:
                break
                
            for category, keyword_list in categories.items():
                if any(keyword.lower() in report_name for keyword in keyword_list):
                    disclosure['category'] = category
                    classified_disclosures[priority].append(disclosure)
                    classified = True
                    break
    
    # 4. 결과 요약
    print(f"\n📊 중요 공시 분류 결과:")
    print(f"  🏆 1순위 (실적/보고서): {len(classified_disclosures['priority_1'])}건")
    print(f"  🚀 2순위 (중대결정): {len(classified_disclosures['priority_2'])}건") 
    print(f"  📈 3순위 (사업흐름): {len(classified_disclosures['priority_3'])}건")
    print(f"  ⚠️ 리스크 신호: {len(classified_disclosures['risk_signals'])}건")
    
    return classified_disclosures


def format_date(date_str):
    """날짜 포맷팅 헬퍼 함수 (YYYYMMDD -> YYYY-MM-DD)"""
    if len(date_str) == 8:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return date_str


def format_priority_disclosures_for_llm(classified_disclosures, company_name):
    """
    중요도별로 분류된 공시 정보를 LLM용으로 포맷팅합니다.
    
    Args:
        classified_disclosures (dict): 분류된 공시 정보.
        company_name (str): 회사명.
        
    Returns:
        str: 포맷팅된 텍스트.
    """
    
    formatted_text = f"### {company_name} 중요 공시 분석\n"
    
    # 1순위: 실적과 직결된 정보
    if classified_disclosures['priority_1']:
        formatted_text += "\n#### 🏆 핵심 실적 정보\n"
        for disclosure in classified_disclosures['priority_1']:
            date = format_date(disclosure.get('rcept_dt', ''))
            report = disclosure.get('report_nm', '')
            category = disclosure.get('category', '')
            
            formatted_text += f"- **{report}** ({date})\n"
            formatted_text += f"  ✓ 분류: {category}\n"
    
    # 2순위: 중대한 경영 결정
    if classified_disclosures['priority_2']:
        formatted_text += "\n#### 🚀 주요 경영 결정\n"
        for disclosure in classified_disclosures['priority_2']:
            date = format_date(disclosure.get('rcept_dt', ''))
            report = disclosure.get('report_nm', '')
            category = disclosure.get('category', '')
            
            formatted_text += f"- **{report}** ({date})\n"
            formatted_text += f"  ✓ 분류: {category}\n"
    
    # 3순위: 사업 흐름
    if classified_disclosures['priority_3']:
        formatted_text += "\n#### 📈 사업 동향\n"
        for disclosure in classified_disclosures['priority_3']:
            date = format_date(disclosure.get('rcept_dt', ''))
            report = disclosure.get('report_nm', '')
            category = disclosure.get('category', '')
            
            formatted_text += f"- **{report}** ({date})\n"
            formatted_text += f"  ✓ 분류: {category}\n"
    
    # 리스크 신호
    if classified_disclosures['risk_signals']:
        formatted_text += "\n#### ⚠️ 주의 사항\n"
        for disclosure in classified_disclosures['risk_signals']:
            date = format_date(disclosure.get('rcept_dt', ''))
            report = disclosure.get('report_nm', '')
            category = disclosure.get('category', '')
            
            formatted_text += f"- **{report}** ({date})\n"
            formatted_text += f"  ✓ 리스크 요인: {category}\n"
    
    # 분석이 없는 경우
    total_important = sum(len(v) for v in classified_disclosures.values())
    if total_important == 0:
        formatted_text += "\n- 최근 90일간 주요 공시가 없습니다.\n"
    
    return formatted_text


def create_smart_company_report(company_name, csv_path='corp_codes.csv'):
    """
    뉴스 + 중요도별 공시 정보를 결합한 스마트 리포트를 생성합니다.
    
    Args:
        company_name (str): 회사명.
        csv_path (str): CSV 파일 경로.
        
    Returns:
        str: LLM용 스마트 컨텍스트 데이터.
    """
    
    print(f"=== {company_name} 스마트 리포트 생성 ===")
    
    # 1. 뉴스 정보 수집
    print("\n1. 최신 뉴스 수집...")
    news_articles = fetch_naver_news(company_name, display_count=5)
    
    news_context = ""
    if news_articles:
        filtered_headlines = []
        for article in news_articles:
            if company_name in article['title'] or company_name in article['description']:
                filtered_headlines.append(article['title'])
        
        if filtered_headlines:
            news_context = f"### {company_name} 최신 뉴스\n"
            news_context += "- " + "\n- ".join(filtered_headlines) + "\n"
    
    # 2. 중요도별 공시 정보 수집
    print("\n2. 중요 공시 분석...")
    classified_disclosures = get_important_disclosures_by_priority(company_name, csv_path)
    disclosure_context = format_priority_disclosures_for_llm(classified_disclosures, company_name)
    
    # 3. 스마트 컨텍스트 생성
    smart_context = f"""
{news_context}

{disclosure_context}

---
※ 분석 기준: 
- 뉴스: 최신 5건 중 관련 뉴스
- 공시: 최근 90일 중요 공시만 선별 분석
- 분류: 실적정보 > 경영결정 > 사업동향 > 리스크신호
"""
    
    print("\n✅ 스마트 리포트 생성 완료!")
    print(f"📈 총 중요 공시: {sum(len(v) for v in classified_disclosures.values())}건")
    
    return smart_context


def create_final_investment_report(company_name, csv_path='corp_codes.csv'):
    """
    최종 투자 리포트를 자동으로 생성하는 함수.
    뉴스 + 중요도별 공시 + LLM 분석을 결합합니다.
    
    Args:
        company_name (str): 회사명.
        csv_path (str): CSV 파일 경로.
        
    Returns:
        dict: 최종 리포트 데이터 (컨텍스트 + 프롬프트).
    """
    
    print(f"🎯 {company_name} 최종 투자 리포트 자동 생성 시작")
    print("="*60)
    
    # 1. 스마트 컨텍스트 데이터 생성
    smart_context = create_smart_company_report(company_name, csv_path)
    
    # 2. 최종 프롬프트 생성
    final_prompt = f"""
# 지시문: 당신은 대한민국 최고의 증권사 애널리스트입니다. 아래 [컨텍스트 데이터]만을 사용하여, '{company_name}'에 대한 투자 리포트를 다음 [리포트 형식]에 맞춰 작성해 주세요. 컨텍스트에 없는 내용은 절대 지어내지 마세요.

# 리포트 형식
## 1. **투자 포인트 요약 (Investment Highlights)**
- 최신 뉴스와 공시를 바탕으로 한 핵심 투자 포인트 3가지

## 2. **실적 및 경영 현황 분석**
- 🏆 최근 실적 정보 분석 (분기/반기 보고서, 영업실적 기준)
- 🚀 주요 경영 결정 분석 (M&A, 증자, 자사주 등)

## 3. **사업 동향 및 성장 동력**
- 📈 신규 계약, 투자 확장 등 미래 성장 요인 분석
- 시장에서의 경쟁력과 포지셔닝

## 4. **리스크 요인**
- ⚠️ 주의해야 할 위험 요소 (소송, 지배구조 변화 등)
- 단기/중기적 우려 사항

## 5. **종합 투자 의견**
- 위 분석을 종합한 투자 관점에서의 최종 의견
- 목표 주가나 구체적 수치 제시 금지 (정성적 평가만)

# 컨텍스트 데이터
{smart_context}

---
※ 주의사항: 위 데이터에 포함되지 않은 정보는 절대 사용하지 마세요.
"""
    
    print("\n🎯 최종 리포트 구성 요소:")
    print("  📰 최신 뉴스 분석")
    print("  🏆 핵심 실적 정보")
    print("  🚀 주요 경영 결정") 
    print("  📈 사업 동향")
    print("  ⚠️ 리스크 요인")
    print("\n✅ 최종 투자 리포트 프롬프트 생성 완료!")
    
    return {
        'company_name': company_name,
        'context_data': smart_context,
        'final_prompt': final_prompt,
        'generation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


def create_comprehensive_company_report(company_name, csv_path='corp_codes.csv'):
    """
    뉴스 + 공시 정보를 결합한 종합 회사 리포트 데이터를 생성합니다.
    (기존 호환성을 위해 유지)
    
    Args:
        company_name (str): 회사명.
        csv_path (str): CSV 파일 경로.
        
    Returns:
        str: LLM용 종합 컨텍스트 데이터.
    """
    
    print(f"=== {company_name} 종합 리포트 데이터 생성 ===")
    
    # 1. 뉴스 정보 수집
    print("\n1. 뉴스 정보 수집 중...")
    news_articles = fetch_naver_news(company_name, display_count=5)
    
    news_context = ""
    if news_articles:
        filtered_headlines = []
        for article in news_articles:
            if company_name in article['title'] or company_name in article['description']:
                filtered_headlines.append(article['title'])
        
        if filtered_headlines:
            news_context = f"### {company_name} 최신 뉴스\n"
            news_context += "- " + "\n- ".join(filtered_headlines) + "\n"
    
    # 2. 공시 정보 수집
    print("\n2. 공시 정보 수집 중...")
    disclosures = get_company_disclosures_by_name(company_name, csv_path, days_back=30, max_count=10)
    disclosure_context = format_disclosures_for_llm(disclosures, company_name)
    
    # 3. 종합 컨텍스트 생성
    comprehensive_context = f"""
{news_context}

{disclosure_context}

---
※ 데이터 기준: 뉴스(최신 5건), 공시(최근 30일)
"""
    
    print("\n✅ 종합 리포트 데이터 생성 완료!")
    return comprehensive_context


def get_kospi_top_100_companies():
    """
    코스피 상위 100개 기업 목록을 반환합니다.
    (시가총액 기준 대략적인 순서, 2024년 기준)
    
    Returns:
        List[str]: 코스피 상위 100개 기업명 리스트
    """
    kospi_top_100 = [
        # Top 10
        "삼성전자", "SK하이닉스", "NAVER", "카카오", "LG에너지솔루션",
        "삼성바이오로직스", "현대자동차", "기아", "삼성SDI", "LG화학",
        
        # 11-20
        "POSCO홀딩스", "삼성물산", "KB금융", "신한지주", "하나금융지주",
        "LG전자", "현대모비스", "셀트리온", "SK이노베이션", "삼성생명보험",
        
        # 21-30
        "한국전력공사", "SK텔레콤", "포스코퓨처엠", "현대중공업", "삼성화재",
        "LG생활건강", "KT&G", "한화솔루션", "고려아연", "삼성에스디에스",
        
        # 31-40
        "아모레퍼시픽", "SK", "두산에너빌리티", "HMM", "한국조선해양",
        "기업은행", "우리금융지주", "현대건설", "삼성전기", "LG이노텍",
        
        # 41-50
        "KT", "한국가스공사", "롯데케미칼", "현대글로비스", "SK스퀘어",
        "한미반도체", "삼성중공업", "포스코인터내셔널", "두산", "현대제철",
        
        # 51-60
        "LG", "한화에어로스페이스", "KB국민은행", "신한은행", "하나은행",
        "코웨이", "크래프톤", "펄어비스", "NCSoft", "넷마블",
        
        # 61-70
        "카카오뱅크", "카카오페이", "컴투스", "위메이드", "넥슨게임즈",
        "삼천리", "GS", "GS칼텍스", "S-Oil", "현대오일뱅크",
        
        # 71-80
        "롯데쇼핑", "롯데칠성음료", "신세계", "이마트", "홈플러스",
        "CJ제일제당", "CJ ENM", "CJ대한통운", "동원시스템즈", "오뚜기",
        
        # 81-90
        "농심", "롯데제과", "한화시스템", "한화생명", "동화약품",
        "유한양행", "녹십자", "셀트리온제약", "대웅제약", "종근당",
        
        # 91-100
        "삼성물산", "포스코DX", "SK머티리얼즈", "LG디스플레이", "삼성디스플레이",
        "SK바이오팜", "한미약품", "일동제약", "부광약품", "대한항공"
    ]
    
    # 중복 제거 및 정확한 100개로 조정
    unique_companies = list(dict.fromkeys(kospi_top_100))  # 순서 유지하면서 중복 제거
    
    if len(unique_companies) > 100:
        unique_companies = unique_companies[:100]
    
    print(f"📈 코스피 상위 {len(unique_companies)}개 기업 목록 로드 완료")
    return unique_companies


def get_custom_company_list(list_type="top_10"):
    """
    다양한 기업 목록을 제공하는 함수
    
    Args:
        list_type (str): 목록 유형
            - "top_10": 상위 10개 기업
            - "top_30": 상위 30개 기업  
            - "top_50": 상위 50개 기업
            - "top_100": 상위 100개 기업
            - "tech_focus": 기술주 중심
            - "finance_focus": 금융주 중심
            
    Returns:
        List[str]: 선택된 기업 목록
    """
    kospi_100 = get_kospi_top_100_companies()
    
    if list_type == "top_10":
        return kospi_100[:10]
    elif list_type == "top_30":
        return kospi_100[:30]
    elif list_type == "top_50":
        return kospi_100[:50]
    elif list_type == "top_100":
        return kospi_100
    elif list_type == "tech_focus":
        tech_companies = [
            "삼성전자", "SK하이닉스", "NAVER", "카카오", "LG에너지솔루션",
            "삼성바이오로직스", "삼성SDI", "LG화학", "LG전자", "셀트리온",
            "삼성에스디에스", "삼성전기", "LG이노텍", "한미반도체", "코웨이",
            "크래프톤", "펄어비스", "NCSoft", "넷마블", "컴투스"
        ]
        return tech_companies
    elif list_type == "finance_focus":
        finance_companies = [
            "KB금융", "신한지주", "하나금융지주", "기업은행", "우리금융지주",
            "KB국민은행", "신한은행", "하나은행", "카카오뱅크", "카카오페이",
            "삼성생명보험", "삼성화재", "한화생명"
        ]
        return finance_companies
    else:
        print(f"❌ 알 수 없는 list_type: {list_type}")
        return kospi_100[:10]  # 기본값


def save_company_list_to_file(companies, filename="target_companies.json"):
    """
    기업 목록을 JSON 파일로 저장
    
    Args:
        companies (List[str]): 기업 목록
        filename (str): 저장할 파일명
    """
    company_data = {
        "created_at": datetime.now().isoformat(),
        "total_companies": len(companies),
        "companies": companies
    }
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(company_data, f, ensure_ascii=False, indent=2)
        print(f"✅ 기업 목록 저장 완료: {filename} ({len(companies)}개 기업)")
    except Exception as e:
        print(f"❌ 파일 저장 실패: {e}")


def load_company_list_from_file(filename="target_companies.json"):
    """
    JSON 파일에서 기업 목록을 로드
    
    Args:
        filename (str): 로드할 파일명
        
    Returns:
        List[str]: 기업 목록
    """
    try:
        if not os.path.exists(filename):
            print(f"❌ 파일이 없습니다: {filename}")
            return []
            
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        companies = data.get('companies', [])
        created_at = data.get('created_at', '')
        
        print(f"✅ 기업 목록 로드 완료: {len(companies)}개 기업 (생성일: {created_at[:10]})")
        return companies
        
    except Exception as e:
        print(f"❌ 파일 로드 실패: {e}")
        return []
