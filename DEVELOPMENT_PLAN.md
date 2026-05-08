# 안전귀가Navi MVP 개발 계획서

## 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 프로젝트명 | 안전귀가Navi (Pre-Living MVP) |
| 목적 | 서울시 1인 가구가 주소 기반으로 안전 인프라 수준을 분석하여 안심 주거환경 점수를 제공 |
| MVP 범위 | 주소 1개 입력 → 안전 점수 산출 + 지도 시각화 + AI 리포트 |
| 데이터 범위 | 서울시 한정 |

---

## 1. 확정된 설계 결정사항

### 1.1 스코어링 방식
- **절대 점수 방식** 채택
- 각 항목별 고정 기준으로 0~100 스케일 정규화

### 1.2 카테고리별 가중치 (인프라 중시)

| 카테고리 | 가중치 | 구성 요소 |
|----------|--------|-----------|
| 감시 인프라 | **30%** | CCTV |
| 야간 조명 | **30%** | 가로등 + 보행등 |
| 긴급 대응 | **20%** | 안전비상벨 |
| 안심정책 접근성 | **10%** | 안심귀갓길 안전시설물 |
| 귀가 접근성 | **10%** | 안심귀갓길 경로 |

### 1.3 데이터 처리 방식
- 로컬 CSV 파일 기반 (일회성 다운로드 후 고정)
- 누락 데이터(null) → 주변 지역 평균값으로 대체
- 시간대별 점수 차등 없음

### 1.4 기술 스택
- **Backend**: Python + FastAPI
- **Spatial Processing**: GeoPandas, Shapely, geopy
- **Database**: 초기 MVP는 로컬 CSV/JSON
- **Map API**: Kakao Map API (Geocoding + 지도 시각화)
- **LLM**: Claude API (리포트 생성)
- **Frontend**: 추후 결정 (React/Next.js 권장)

---

## 2. 데이터 명세

### 2.1 필수 데이터셋

| # | 데이터명 | 출처 | 용도 | 주요 필드 |
|---|----------|------|------|-----------|
| 1 | 전국 CCTV 표준데이터 | data.go.kr | 감시 인프라 | 위도, 경도, 설치목적, 관리기관 |
| 2 | 서울시 가로등 위치 정보 | data.seoul.go.kr | 야간 조명 | 위도, 경도, 등주번호 |
| 3 | 서울시 가로등 점소등 시간 현황 | data.seoul.go.kr | (참조용) | 점등시간, 소등시간 |
| 4 | 서울특별시 보행등 위도경도 현황 | data.go.kr | 야간 조명 보완 | 위도, 경도 |
| 5 | 행정안전부 안전비상벨 위치정보 | data.go.kr | 긴급 대응 | 위도, 경도, 설치장소 |
| 6 | 서울시 안심귀갓길 안전시설물 | data.seoul.go.kr | 안심정책 | 위도, 경도, 시설유형 |
| 7 | 서울시 안심귀갓길 경로 | data.seoul.go.kr | 귀가 접근성 | 경로 좌표 (LineString) |

### 2.2 데이터 전처리 요구사항

```
1. 모든 데이터를 서울시로 필터링
2. 좌표계 통일 (WGS84 / EPSG:4326)
3. 위도/경도 컬럼명 표준화: lat, lng
4. null 좌표 레코드 제거
5. CSV → GeoDataFrame 변환
```

---

## 3. 스코어링 로직 상세

### 3.1 반경별 분석 기준

| 반경 | 의미 | 적용 대상 |
|------|------|-----------|
| 50m | 집 바로 앞 | 가로등/보행등 |
| 100m | 초근접 인프라 | 가로등/보행등, CCTV |
| 300m | 일상 보행권 | CCTV, 비상벨, 안심시설물 |
| 500m | 생활권 | 안심귀갓길 경로 |

### 3.2 Feature 정의

#### 감시 인프라 (30점 만점)
| Feature | 설명 | 정규화 기준 |
|---------|------|-------------|
| cctv_100m_count | 100m 내 CCTV 수 | 5개 이상 → 100점 |
| cctv_300m_count | 300m 내 CCTV 수 | 15개 이상 → 100점 |
| nearest_cctv_distance | 가장 가까운 CCTV 거리 | 50m 이하 → 100점, 300m 이상 → 0점 |

**카테고리 점수** = (cctv_100m_score × 0.3 + cctv_300m_score × 0.4 + nearest_cctv_score × 0.3) × 0.30

#### 야간 조명 (30점 만점)
| Feature | 설명 | 정규화 기준 |
|---------|------|-------------|
| streetlight_50m_count | 50m 내 가로등 수 | 3개 이상 → 100점 |
| streetlight_100m_count | 100m 내 가로등 수 | 8개 이상 → 100점 |
| walklight_100m_count | 100m 내 보행등 수 | 5개 이상 → 100점 |

**카테고리 점수** = (light_50m_score × 0.4 + light_100m_score × 0.3 + walklight_score × 0.3) × 0.30

#### 긴급 대응 (20점 만점)
| Feature | 설명 | 정규화 기준 |
|---------|------|-------------|
| emergencybell_300m_count | 300m 내 비상벨 수 | 3개 이상 → 100점 |
| nearest_emergencybell_distance | 가장 가까운 비상벨 거리 | 100m 이하 → 100점, 500m 이상 → 0점 |

**카테고리 점수** = (bell_count_score × 0.5 + bell_distance_score × 0.5) × 0.20

#### 안심정책 접근성 (10점 만점)
| Feature | 설명 | 정규화 기준 |
|---------|------|-------------|
| safe_facility_300m_count | 300m 내 안심시설물 수 | 3개 이상 → 100점 |

**카테고리 점수** = safe_facility_score × 0.10

#### 귀가 접근성 (10점 만점)
| Feature | 설명 | 정규화 기준 |
|---------|------|-------------|
| nearest_safe_route_distance | 가장 가까운 안심귀갓길 거리 | 100m 이하 → 100점, 500m 이상 → 0점 |
| safe_route_exists_500m | 500m 내 안심귀갓길 존재 여부 | 있음 → 100점, 없음 → 0점 |

**카테고리 점수** = (route_distance_score × 0.6 + route_exists_score × 0.4) × 0.10

### 3.3 총점 계산

```python
total_score = (
    surveillance_score +  # 30점 만점
    lighting_score +      # 30점 만점
    emergency_score +     # 20점 만점
    safe_policy_score +   # 10점 만점
    route_access_score    # 10점 만점
)
# 총점: 0~100점
```

### 3.4 등급 기준

| 점수 범위 | 등급 | 설명 |
|-----------|------|------|
| 85~100 | 매우 양호 | 안전 인프라가 충분히 갖춰진 지역 |
| 70~84 | 양호 | 대부분의 안전 인프라가 갖춰진 지역 |
| 55~69 | 보통 | 기본적인 안전 인프라가 있는 지역 |
| 40~54 | 미흡 | 일부 안전 인프라가 부족한 지역 |
| 0~39 | 취약 | 안전 인프라 보강이 필요한 지역 |

---

## 4. API 설계

### 4.1 엔드포인트 목록

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/safety-score` | 주소 기반 안전 점수 조회 |
| GET | `/api/v1/health` | 서버 상태 확인 |

### 4.2 POST /api/v1/safety-score

#### Request
```json
{
  "address": "서울특별시 관악구 신림동 123-45"
}
```

#### Response (200 OK)
```json
{
  "success": true,
  "data": {
    "address": "서울특별시 관악구 신림동 123-45",
    "coordinates": {
      "lat": 37.4847,
      "lng": 126.9291
    },
    "total_score": 72,
    "grade": "양호",
    "category_scores": {
      "surveillance": {
        "score": 24.5,
        "max": 30,
        "percentage": 82
      },
      "lighting": {
        "score": 21.0,
        "max": 30,
        "percentage": 70
      },
      "emergency": {
        "score": 14.0,
        "max": 20,
        "percentage": 70
      },
      "safe_policy": {
        "score": 6.0,
        "max": 10,
        "percentage": 60
      },
      "route_access": {
        "score": 6.5,
        "max": 10,
        "percentage": 65
      }
    },
    "evidence": {
      "cctv_100m_count": 3,
      "cctv_300m_count": 12,
      "nearest_cctv_distance_m": 45,
      "streetlight_50m_count": 2,
      "streetlight_100m_count": 6,
      "walklight_100m_count": 3,
      "emergencybell_300m_count": 2,
      "nearest_emergencybell_distance_m": 120,
      "safe_facility_300m_count": 2,
      "nearest_safe_route_distance_m": 180,
      "safe_route_exists_500m": true
    },
    "ai_report": "이 주소는 전반적으로 양호한 안전 인프라 환경을 갖추고 있습니다. 반경 100m 내에 CCTV 3대가 설치되어 있어 감시 환경이 양호하며, 가장 가까운 CCTV는 약 45m 거리에 있습니다. 야간 조명의 경우 50m 내 가로등 2개, 100m 내 보행등 3개가 확인되어 기본적인 조명 환경이 갖춰져 있습니다. 긴급 상황 시 약 120m 거리에 안전비상벨이 위치해 있습니다. 다만, 안심귀갓길까지의 거리가 180m로 다소 떨어져 있어, 야간 귀가 시에는 주요 도로를 이용하시는 것을 권장드립니다."
  }
}
```

#### Response (400 Bad Request)
```json
{
  "success": false,
  "error": {
    "code": "INVALID_ADDRESS",
    "message": "주소를 찾을 수 없습니다. 서울시 내 정확한 주소를 입력해주세요."
  }
}
```

#### Response (400 Bad Request - 서울 외 지역)
```json
{
  "success": false,
  "error": {
    "code": "OUT_OF_COVERAGE",
    "message": "현재 서비스는 서울시 지역만 지원합니다."
  }
}
```

---

## 5. 프로젝트 구조

```
safe-return-navi/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
│
├── data/                          # 데이터 저장소
│   ├── raw/                       # 원본 데이터
│   │   ├── cctv_seoul.csv
│   │   ├── streetlight.csv
│   │   ├── walklight.csv
│   │   ├── emergency_bell.csv
│   │   ├── safe_facility.csv
│   │   └── safe_route.csv
│   └── processed/                 # 전처리된 데이터
│       └── *.geojson
│
├── src/
│   ├── __init__.py
│   ├── main.py                    # FastAPI 앱 진입점
│   ├── config.py                  # 설정 관리
│   │
│   ├── api/                       # API 라우터
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── health.py
│   │       └── safety_score.py
│   │
│   ├── core/                      # 핵심 비즈니스 로직
│   │   ├── __init__.py
│   │   ├── scoring/
│   │   │   ├── __init__.py
│   │   │   ├── calculator.py      # 점수 계산 엔진
│   │   │   ├── normalizer.py      # 점수 정규화
│   │   │   └── weights.py         # 가중치 설정
│   │   └── spatial/
│   │       ├── __init__.py
│   │       ├── analyzer.py        # 공간 분석 (반경 검색)
│   │       └── geocoder.py        # 주소 → 좌표 변환
│   │
│   ├── data/                      # 데이터 처리
│   │   ├── __init__.py
│   │   ├── loader.py              # 데이터 로드
│   │   └── preprocessor.py        # 전처리
│   │
│   ├── services/                  # 외부 서비스 연동
│   │   ├── __init__.py
│   │   ├── kakao_map.py           # Kakao Map API
│   │   └── claude_ai.py           # Claude API (리포트 생성)
│   │
│   └── models/                    # Pydantic 모델
│       ├── __init__.py
│       ├── request.py
│       └── response.py
│
├── scripts/                       # 유틸리티 스크립트
│   ├── download_data.py           # 데이터 다운로드
│   └── preprocess_data.py         # 데이터 전처리
│
├── tests/                         # 테스트
│   ├── __init__.py
│   ├── test_scoring.py
│   ├── test_spatial.py
│   └── test_api.py
│
└── frontend/                      # 프론트엔드 (추후 구현)
    └── ...
```

---

## 6. 구현 단계별 계획

### Phase 1: 환경 설정 및 데이터 준비 (Day 1-2)

#### Step 1.1: 프로젝트 초기화
- [ ] 프로젝트 폴더 구조 생성
- [ ] Python 가상환경 설정
- [ ] requirements.txt 작성 및 의존성 설치
- [ ] .env 설정 (API 키)

#### Step 1.2: 데이터 다운로드
- [ ] 7개 데이터셋 다운로드
- [ ] data/raw/ 폴더에 저장

#### Step 1.3: 데이터 전처리
- [ ] 서울시 데이터 필터링
- [ ] 좌표계 통일 (WGS84)
- [ ] 컬럼명 표준화
- [ ] GeoDataFrame 변환
- [ ] data/processed/ 에 저장

### Phase 2: 핵심 엔진 구현 (Day 3-5)

#### Step 2.1: Geocoding 모듈
- [ ] Kakao Map API 연동
- [ ] 주소 → 좌표 변환 함수
- [ ] 서울시 범위 검증

#### Step 2.2: 공간 분석 모듈
- [ ] 반경 내 포인트 검색 함수
- [ ] 최근접 거리 계산 함수
- [ ] 경로(LineString) 거리 계산

#### Step 2.3: 스코어링 엔진
- [ ] Feature 계산 함수
- [ ] 정규화 함수
- [ ] 카테고리별 점수 계산
- [ ] 총점 및 등급 계산

### Phase 3: API 구현 (Day 6-7)

#### Step 3.1: FastAPI 설정
- [ ] FastAPI 앱 초기화
- [ ] CORS 설정
- [ ] 에러 핸들러

#### Step 3.2: 엔드포인트 구현
- [ ] POST /api/v1/safety-score
- [ ] GET /api/v1/health

#### Step 3.3: Claude API 연동
- [ ] 리포트 생성 프롬프트 설계
- [ ] API 호출 및 응답 처리

### Phase 4: 프론트엔드 구현 (Day 8-10)

#### Step 4.1: 기본 UI
- [ ] 주소 입력 폼
- [ ] 결과 표시 영역

#### Step 4.2: 지도 시각화
- [ ] Kakao Maps SDK 연동
- [ ] 주소 마커 표시
- [ ] 주변 인프라 마커 표시 (CCTV, 가로등 등)
- [ ] 반경 원 표시

#### Step 4.3: 결과 UI
- [ ] 점수 대시보드
- [ ] 카테고리별 상세 점수
- [ ] AI 리포트 표시

### Phase 5: 테스트 및 마무리 (Day 11-12)

#### Step 5.1: 테스트
- [ ] 단위 테스트 작성
- [ ] 통합 테스트
- [ ] 엣지 케이스 테스트

#### Step 5.2: 문서화
- [ ] API 문서 (Swagger)
- [ ] README 작성

---

## 7. 데이터 흐름도 (DFD Level 1)

```
┌─────────────┐     주소      ┌──────────────────┐
│    User     │─────────────▶│   FastAPI App    │
└─────────────┘               └────────┬─────────┘
                                       │
                              ┌────────▼─────────┐
                              │  Kakao Map API   │
                              │   (Geocoding)    │
                              └────────┬─────────┘
                                       │ 좌표(lat, lng)
                              ┌────────▼─────────┐
                              │  Spatial Analyzer │
                              │  (GeoPandas)     │
                              └────────┬─────────┘
                                       │
            ┌──────────────────────────┼──────────────────────────┐
            │                          │                          │
    ┌───────▼───────┐         ┌───────▼───────┐         ┌───────▼───────┐
    │  CCTV Data    │         │ Streetlight   │         │ Emergency     │
    │  (GeoJSON)    │         │ Data (GeoJSON)│         │ Bell (GeoJSON)│
    └───────┬───────┘         └───────┬───────┘         └───────┬───────┘
            │                          │                          │
            └──────────────────────────┼──────────────────────────┘
                                       │ Features
                              ┌────────▼─────────┐
                              │  Scoring Engine  │
                              └────────┬─────────┘
                                       │ Scores
                              ┌────────▼─────────┐
                              │   Claude API     │
                              │ (Report Gen)     │
                              └────────┬─────────┘
                                       │ AI Report
                              ┌────────▼─────────┐
                              │     Response     │
                              └────────┬─────────┘
                                       │
┌─────────────┐    점수+리포트   ┌──────▼──────────┐
│    User     │◀─────────────────│   Frontend      │
└─────────────┘                  └─────────────────┘
```

---

## 8. 리스크 및 대응 방안

| 리스크 | 영향도 | 대응 방안 |
|--------|--------|-----------|
| 데이터 다운로드 실패 | 높음 | 수동 다운로드 백업, 캐시 저장 |
| Kakao API 호출 한도 초과 | 중간 | 캐싱 적용, 호출 최적화 |
| 좌표 데이터 품질 불량 | 중간 | 전처리 단계에서 이상치 제거 |
| 안심귀갓길 없는 지역 | 낮음 | 주변 평균값 대체, 해당 카테고리 0점 처리 |
| Claude API 응답 지연 | 낮음 | 타임아웃 설정, 기본 템플릿 fallback |

---

## 9. 다음 단계

이 계획서가 확정되면:

1. **Phase 1 시작**: 프로젝트 구조 생성 및 데이터 다운로드
2. **데이터 확보**: 7개 데이터셋 다운로드 필요
3. **API 키 준비**: Kakao Map API, Claude API 키 필요

---

*작성일: 2026-05-08*
*버전: 1.0*
