# 🚀 OpenAI 모델 파인튜닝 완전 가이드

## 📋 현재 상태
✅ **96개 기업 데이터셋 준비 완료**: `offline_investment_reports_dataset.jsonl`  
✅ **RAG 시스템 구축 완료**: Producer-Consumer 아키텍처  
✅ **고품질 데이터**: 일관된 투자 분석 템플릿  

---

## 🎯 Step-by-Step 파인튜닝 실행

### **1단계: OpenAI API 키 준비**
1. https://platform.openai.com/account/api-keys 에서 API 키 발급
2. 결제 정보 등록 (파인튜닝은 유료 서비스)
3. API 키를 안전한 곳에 보관

### **2단계: 환경 설정**
```bash
# Python 패키지 설치
pip install openai

# API 키 환경변수 설정 (Windows)
set OPENAI_API_KEY=your-api-key-here

# 또는 PowerShell
$env:OPENAI_API_KEY="your-api-key-here"
```

### **3단계: 파인튜닝 실행 (CLI 방법)**
```bash
# 파일 업로드
openai api files.create -f offline_investment_reports_dataset.jsonl -p fine-tune

# 파인튜닝 시작
openai api fine_tuning.jobs.create -t file-xxxxx -m gpt-3.5-turbo --suffix "korean-investment-analyst"

# 진행 상황 확인
openai api fine_tuning.jobs.list
openai api fine_tuning.jobs.follow -i ftjob-xxxxx
```

### **4단계: Python 코드로 실행**
노트북의 마지막 셀에 있는 Python 코드 사용:
1. `OPENAI_API_KEY` 변수에 실제 API 키 입력
2. 각 단계별로 함수 실행:
   - `upload_training_file()` → 파일 업로드
   - `start_fine_tuning()` → 파인튜닝 시작
   - `check_fine_tuning_status()` → 상태 확인
   - `test_fine_tuned_model()` → 완료된 모델 테스트

---

## ⏱️ 예상 소요시간 및 비용

### **시간**
- **데이터 업로드**: 1-2분
- **파인튜닝 실행**: 15-25분 (96개 데이터 기준)
- **모델 배포**: 2-3분
- **총 소요시간**: **약 20-30분**

### **비용** (2024년 기준)
- **훈련 비용**: $0.008/1K 토큰 (GPT-3.5-turbo)
- **예상 훈련 비용**: $8-15
- **사용 비용**: 기본 요금 + 추가 요금/토큰

---

## 🎁 파인튜닝 완료 후 활용

### **1. 전문 투자 분석가 봇**
```python
# 한국 기업 전문 분석
response = openai.ChatCompletion.create(
    model="ft:gpt-3.5-turbo:your-org:korean-investment-analyst:xxxxx",
    messages=[
        {"role": "system", "content": "당신은 전문 증권 애널리스트입니다."},
        {"role": "user", "content": "카카오에 대한 투자 분석을 해주세요."}
    ]
)
```

### **2. 자동 리포트 생성 서비스**
- 매일 아침 주요 기업 분석 리포트 자동 생성
- 뉴스 기반 실시간 투자 의견 업데이트
- 개인 맞춤형 포트폴리오 분석

### **3. 금융 데이터 분석 API**
- 웹서비스나 앱에 통합
- 실시간 주식 분석 기능
- 전문가 수준의 투자 조언 제공

---

## 📈 기대 효과

### **Before (일반 GPT)**
- 일반적인 투자 상식 수준
- 한국 기업 정보 부족
- 일관성 없는 분석 형식

### **After (파인튜닝된 모델)**
- ✅ **96개 한국 기업 전문 지식**
- ✅ **증권사 수준의 분석 품질**
- ✅ **일관된 리포트 형식**
- ✅ **투자 분석 → 리스크 평가 → 최종 의견 구조**
- ✅ **전문 금융 용어 활용**

---

## 🔧 고급 설정

### **하이퍼파라미터 최적화**
```json
{
  "n_epochs": 3,
  "batch_size": 1,
  "learning_rate_multiplier": 0.1,
  "prompt_loss_weight": 0.01
}
```

### **검증 데이터셋 분리**
- 전체 96개 중 10%인 10개를 검증용으로 분리
- 과적합 방지 및 성능 검증

### **모델 성능 모니터링**
- 훈련 손실(Training Loss) 추적
- 검증 손실(Validation Loss) 모니터링
- 조기 종료(Early Stopping) 적용

---

## 🎯 다음 단계

1. **파인튜닝 실행** → 위 가이드 따라 진행
2. **모델 테스트** → 다양한 기업으로 품질 검증
3. **성능 최적화** → 하이퍼파라미터 조정
4. **프로덕션 배포** → 실제 서비스에 적용
5. **지속적 개선** → 새로운 데이터로 재훈련

**🎉 축하합니다! 완전한 AI 투자 분석가를 만들 준비가 되었습니다!**
