# 안전귀가Navi

서울시 1인 가구를 위한 AI 기반 안심 주거환경 점수 분석 서비스

## 프로젝트 개요

서울시 내 특정 주소의 안전지원 인프라 수준을 데이터 기반으로 분석하여 "안심 주거환경 점수"를 제공합니다.

### 분석 항목

| 카테고리 | 가중치 | 데이터 |
|----------|--------|--------|
| 감시 인프라 | 30% | CCTV |
| 야간 조명 | 30% | 가로등, 보행등 |
| 긴급 대응 | 20% | 안전비상벨 |
| 안심정책 접근성 | 10% | 안심귀갓길 시설물 |
| 귀가 접근성 | 10% | 안심귀갓길 경로 |

## 설치 방법

### 1. 환경 설정

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 가상환경 활성화 (Mac/Linux)
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정

```bash
# .env.example을 .env로 복사
cp .env.example .env

# .env 파일을 편집하여 API 키 입력
# KAKAO_REST_API_KEY=your_kakao_api_key
# ANTHROPIC_API_KEY=your_anthropic_api_key
```

### 3. 데이터 준비

```bash
# 데이터 파일 체크
python scripts/download_data.py

# 다운로드 가이드 확인
python scripts/download_data.py --guide

# 데이터 전처리
python scripts/preprocess_data.py
```

### 4. 서버 실행

```bash
# 개발 서버 실행
uvicorn src.main:app --reload

# 또는
python -m src.main
```

서버가 실행되면 http://localhost:8000 에서 API에 접근할 수 있습니다.

- API 문서: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 사용법

### POST /api/v1/safety-score

주소 기반 안전 점수 조회

**Request:**
```json
{
  "address": "서울특별시 관악구 신림동 123-45"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "address": "서울특별시 관악구 신림동 123-45",
    "coordinates": {"lat": 37.4847, "lng": 126.9291},
    "total_score": 72,
    "grade": "양호",
    "category_scores": {
      "surveillance": {"score": 24.5, "max": 30, "percentage": 82},
      "lighting": {"score": 21.0, "max": 30, "percentage": 70},
      "emergency": {"score": 14.0, "max": 20, "percentage": 70},
      "safe_policy": {"score": 6.0, "max": 10, "percentage": 60},
      "route_access": {"score": 6.5, "max": 10, "percentage": 65}
    },
    "evidence": {
      "cctv_100m_count": 3,
      "cctv_300m_count": 12,
      "streetlight_50m_count": 2,
      ...
    },
    "ai_report": "이 주소는 전반적으로 양호한 안전 인프라 환경을 갖추고 있습니다..."
  }
}
```

## 프로젝트 구조

```
safe-return-navi/
├── src/
│   ├── api/routes/        # API 엔드포인트
│   ├── core/
│   │   ├── scoring/       # 점수 계산 엔진
│   │   └── spatial/       # 공간 분석
│   ├── data/              # 데이터 로드/전처리
│   ├── models/            # Pydantic 모델
│   └── services/          # 외부 서비스 연동
├── data/
│   ├── raw/               # 원본 데이터
│   └── processed/         # 전처리된 데이터
├── scripts/               # 유틸리티 스크립트
└── tests/                 # 테스트
```

## 데이터 출처

- 전국 CCTV 표준데이터 (공공데이터포털)
- 서울시 가로등 위치 정보 (서울 열린데이터 광장)
- 서울특별시 보행등 위도경도 현황 (공공데이터포털)
- 행정안전부 안전비상벨 위치정보 (공공데이터포털)
- 서울시 안심귀갓길 안전시설물 (서울 열린데이터 광장)
- 서울시 안심귀갓길 경로 (서울 열린데이터 광장)

## 테스트

```bash
pytest tests/
```

## 라이선스

MIT License
