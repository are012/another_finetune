# pipeline_update.py - 데이터 수집 및 벡터 DB 구축 (Producer)
"""
기업 분석 데이터 파이프라인 - 생산자 (Producer)

이 스크립트는 백그라운드에서 주기적으로 실행되며, 다음 작업을 수행합니다:
1. 지정된 기업 목록에 대해 최신 뉴스 및 DART 공시 정보 수집
2. 수집된 데이터를 청크 단위로 분할
3. 벡터화하여 로컬 ChromaDB에 저장
4. 파인튜닝 데이터셋 생성을 위한 메타데이터 포함

사용법:
    python pipeline_update.py
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

# LangChain 관련 임포트
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document

# 우리의 데이터 수집 모듈
import data_collector as dc
import importlib

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataPipeline:
    """데이터 수집 및 벡터 DB 구축을 담당하는 메인 클래스"""
    
    def __init__(self, google_api_key: str, db_dir: str = "rag_db"):
        """
        초기화
        
        Args:
            google_api_key (str): Google AI API 키
            db_dir (str): 벡터 DB 저장 디렉토리
        """
        self.google_api_key = google_api_key
        self.db_dir = db_dir
        
        # 임베딩 모델 초기화
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=google_api_key
        )
        
        # 텍스트 분할기 초기화 (파인튜닝에 적합한 청크 크기)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,  # 파인튜닝에 적합한 크기
            chunk_overlap=100,  # 컨텍스트 유지를 위한 오버랩
            separators=["\n\n", "\n", ".", "!", "?", ";", ":", " ", ""]
        )
        
        # 분석 대상 기업 목록 (쉽게 확장 가능)
        self.target_companies = [
            "삼성전자",
            "SK하이닉스",
            "NAVER",
            "카카오",
            "LG에너지솔루션"
        ]
        
        logger.info(f"데이터 파이프라인 초기화 완료. DB 디렉토리: {self.db_dir}")
    
    def collect_company_data(self, company_name: str) -> Dict[str, Any]:
        """
        특정 기업의 최신 데이터 수집
        
        Args:
            company_name (str): 기업명
            
        Returns:
            Dict[str, Any]: 수집된 데이터와 메타데이터
        """
        logger.info(f"📊 {company_name} 데이터 수집 시작...")
        
        collected_data = {
            "company_name": company_name,
            "collection_timestamp": datetime.now().isoformat(),
            "news_data": [],
            "disclosure_data": [],
            "summary_stats": {}
        }
        
        try:
            # 1. 최신 뉴스 수집
            logger.info(f"  📰 뉴스 데이터 수집 중...")
            news_articles = dc.fetch_naver_news(company_name, display_count=10)
            
            for article in news_articles:
                # 뉴스 데이터에 메타데이터 추가
                if company_name in article['title'] or company_name in article['description']:
                    collected_data["news_data"].append({
                        "title": article['title'],
                        "description": article['description'],
                        "source": "naver_news",
                        "company": company_name,
                        "collection_date": datetime.now().isoformat()
                    })
            
            logger.info(f"  ✅ 뉴스 {len(collected_data['news_data'])}건 수집 완료")
            
            # 2. DART 공시 정보 수집 (중요도별 분류)
            logger.info(f"  🏢 공시 데이터 수집 중...")
            try:
                classified_disclosures = dc.get_important_disclosures_by_priority(
                    company_name, days_back=30
                )
                
                if classified_disclosures:
                    for priority, disclosures in classified_disclosures.items():
                        for disclosure in disclosures:
                            collected_data["disclosure_data"].append({
                                "report_name": disclosure.get('report_nm', ''),
                                "reception_date": disclosure.get('rcept_dt', ''),
                                "priority": priority,
                                "source": "dart_api",
                                "company": company_name,
                                "collection_date": datetime.now().isoformat()
                            })
                
                logger.info(f"  ✅ 공시 {len(collected_data['disclosure_data'])}건 수집 완료")
                
            except Exception as e:
                logger.warning(f"  ⚠️ 공시 데이터 수집 실패: {e}")
            
            # 3. 수집 통계
            collected_data["summary_stats"] = {
                "total_news": len(collected_data["news_data"]),
                "total_disclosures": len(collected_data["disclosure_data"]),
                "collection_success": True
            }
            
        except Exception as e:
            logger.error(f"❌ {company_name} 데이터 수집 실패: {e}")
            collected_data["summary_stats"]["collection_success"] = False
            
        return collected_data
    
    def create_documents(self, company_data: Dict[str, Any]) -> List[Document]:
        """
        수집된 데이터를 LangChain Document 형태로 변환
        
        Args:
            company_data (Dict[str, Any]): 수집된 기업 데이터
            
        Returns:
            List[Document]: LangChain Document 리스트
        """
        documents = []
        company_name = company_data["company_name"]
        collection_time = company_data["collection_timestamp"]
        
        # 1. 뉴스 데이터를 Document로 변환
        for news in company_data["news_data"]:
            content = f"""제목: {news['title']}
내용: {news['description']}

기업: {company_name}
출처: 네이버 뉴스
수집일시: {news['collection_date']}"""
            
            metadata = {
                "company": company_name,
                "source": "news",
                "title": news['title'],
                "collection_date": collection_time,
                "data_type": "news_article"
            }
            
            documents.append(Document(page_content=content, metadata=metadata))
        
        # 2. 공시 데이터를 Document로 변환
        for disclosure in company_data["disclosure_data"]:
            content = f"""공시명: {disclosure['report_name']}
접수일자: {disclosure['reception_date']}
중요도: {disclosure['priority']}

기업: {company_name}
출처: DART 공시시스템
수집일시: {disclosure['collection_date']}"""
            
            metadata = {
                "company": company_name,
                "source": "disclosure",
                "priority": disclosure['priority'],
                "report_name": disclosure['report_name'],
                "collection_date": collection_time,
                "data_type": "disclosure_info"
            }
            
            documents.append(Document(page_content=content, metadata=metadata))
        
        logger.info(f"  📄 {company_name}: {len(documents)}개 문서 생성 완료")
        return documents
    
    def split_and_store_documents(self, documents: List[Document]) -> int:
        """
        문서를 청크로 분할하고 벡터 DB에 저장
        
        Args:
            documents (List[Document]): 저장할 문서 리스트
            
        Returns:
            int: 저장된 청크 수
        """
        if not documents:
            return 0
        
        # 문서 분할
        split_docs = self.text_splitter.split_documents(documents)
        logger.info(f"  ✂️ 문서 분할 완료: {len(split_docs)}개 청크 생성")
        
        # ChromaDB에 저장 (기존 DB에 추가)
        try:
            if os.path.exists(self.db_dir):
                # 기존 DB 로드하여 추가
                vectorstore = Chroma(
                    persist_directory=self.db_dir,
                    embedding_function=self.embeddings
                )
                vectorstore.add_documents(split_docs)
            else:
                # 새 DB 생성
                vectorstore = Chroma.from_documents(
                    split_docs,
                    embedding=self.embeddings,
                    persist_directory=self.db_dir
                )
            
            # 변경사항 저장
            vectorstore.persist()
            logger.info(f"  💾 벡터 DB 저장 완료: {len(split_docs)}개 청크")
            
            return len(split_docs)
            
        except Exception as e:
            logger.error(f"❌ 벡터 DB 저장 실패: {e}")
            return 0
    
    def run_pipeline(self) -> Dict[str, Any]:
        """
        전체 데이터 파이프라인 실행
        
        Returns:
            Dict[str, Any]: 실행 결과 통계
        """
        logger.info("🚀 데이터 파이프라인 실행 시작")
        
        pipeline_stats = {
            "start_time": datetime.now().isoformat(),
            "companies_processed": [],
            "total_documents": 0,
            "total_chunks": 0,
            "errors": []
        }
        
        # data_collector 모듈 최신 버전으로 리로드
        importlib.reload(dc)
        
        # 각 기업별 데이터 수집 및 저장
        for company in self.target_companies:
            try:
                # 1. 데이터 수집
                company_data = self.collect_company_data(company)
                
                if company_data["summary_stats"]["collection_success"]:
                    # 2. Document 생성
                    documents = self.create_documents(company_data)
                    
                    # 3. 분할 및 저장
                    chunk_count = self.split_and_store_documents(documents)
                    
                    # 통계 업데이트
                    pipeline_stats["companies_processed"].append({
                        "company": company,
                        "documents": len(documents),
                        "chunks": chunk_count,
                        "success": True
                    })
                    
                    pipeline_stats["total_documents"] += len(documents)
                    pipeline_stats["total_chunks"] += chunk_count
                    
                    logger.info(f"✅ {company} 처리 완료 - 문서: {len(documents)}, 청크: {chunk_count}")
                    
                else:
                    pipeline_stats["errors"].append(f"{company}: 데이터 수집 실패")
                    
            except Exception as e:
                error_msg = f"{company}: {str(e)}"
                pipeline_stats["errors"].append(error_msg)
                logger.error(f"❌ {error_msg}")
        
        pipeline_stats["end_time"] = datetime.now().isoformat()
        pipeline_stats["duration_minutes"] = (
            datetime.fromisoformat(pipeline_stats["end_time"]) - 
            datetime.fromisoformat(pipeline_stats["start_time"])
        ).total_seconds() / 60
        
        # 결과 저장 (파인튜닝 데이터셋 관리용)
        self.save_pipeline_log(pipeline_stats)
        
        logger.info("🎉 데이터 파이프라인 실행 완료!")
        logger.info(f"  처리된 기업: {len(pipeline_stats['companies_processed'])}개")
        logger.info(f"  총 문서: {pipeline_stats['total_documents']}개")
        logger.info(f"  총 청크: {pipeline_stats['total_chunks']}개")
        logger.info(f"  소요시간: {pipeline_stats['duration_minutes']:.1f}분")
        
        return pipeline_stats
    
    def save_pipeline_log(self, stats: Dict[str, Any]) -> None:
        """파이프라인 실행 로그 저장 (파인튜닝 데이터셋 추적용)"""
        log_file = "pipeline_logs.json"
        
        # 기존 로그 로드
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        else:
            logs = []
        
        # 새 로그 추가
        logs.append(stats)
        
        # 최근 50개 로그만 유지
        logs = logs[-50:]
        
        # 저장
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)

def main():
    """메인 실행 함수"""
    # Google API 키 설정 (환경변수 또는 직접 입력)
    GOOGLE_API_KEY = "AIzaSyBwcmK-DKRCI2r8xhHygSfu2GQ-oqK6t_4"  # 실제 키로 교체 필요
    
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "YOUR_GOOGLE_API_KEY":
        print("❌ Google API 키를 설정해주세요!")
        print("GOOGLE_API_KEY 변수에 실제 API 키를 입력하세요.")
        return
    
    try:
        # 파이프라인 실행
        pipeline = DataPipeline(google_api_key=GOOGLE_API_KEY)
        results = pipeline.run_pipeline()
        
        # 결과 출력
        print("\n" + "="*60)
        print("📊 파이프라인 실행 결과")
        print("="*60)
        print(f"처리된 기업 수: {len(results['companies_processed'])}")
        print(f"총 생성 문서: {results['total_documents']}")
        print(f"총 벡터 청크: {results['total_chunks']}")
        print(f"소요 시간: {results['duration_minutes']:.1f}분")
        
        if results['errors']:
            print(f"\n⚠️ 오류 발생: {len(results['errors'])}건")
            for error in results['errors']:
                print(f"  - {error}")
        
        print("\n🎯 다음 단계:")
        print("  1. report_generator.ipynb 노트북 실행")
        print("  2. 생성된 리포트를 파인튜닝 데이터셋으로 활용")
        print("  3. 정기적으로 이 스크립트 재실행하여 데이터 업데이트")
        
    except Exception as e:
        logger.error(f"❌ 파이프라인 실행 실패: {e}")
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    main()
