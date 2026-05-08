# 안전귀가Navi — Processed Data Dictionary

Day 2 전처리 산출물의 스키마 명세. Day 3 이후 모든 모듈이 이 구조에 의존함.

---

## 1. `all_facilities.parquet`

**행 수:** 100,670  
**좌표계:** EPSG:4326 (WGS84)

| 컬럼 | 타입 | 설명 | 예시 |
|---|---|---|---|
| `type` | str | 시설 종류 4종 — 점수 항목과 직접 매핑 | `cctv` / `light` / `bell` / `facility` |
| `sub_type` | str | 세부 분류 (점수 가중치 보정용) | `생활방범`, `가로변`, `안심귀갓길_CCTV` |
| `lat` | float64 | WGS84 위도 | 37.5814 |
| `lon` | float64 | WGS84 경도 | 126.9686 |
| `gu` | str/NA | 자치구 (가로등은 NA — 좌표만 제공) | `종로구` |
| `dong` | str/NA | 행정동 | `누하동` |
| `source` | str | 원본 데이터셋 | `cctv_national` / `streetlight_seoul` / `emergency_bell` / `safe_route_facility` |
| `extra` | str | 원본 추가 정보 (JSON 문자열) | `{"camera_count": 4, "manager": "종로구청"}` |

### type별 분포 (검증 완료)

| type | 건수 | 점수 항목 | 데이터 소스 |
|---|---:|---|---|
| cctv | 50,238 | 감시 인프라 | 전국CCTV표준(48,751) + 안심귀갓길 시설물 코드302(1,487) |
| bell | 21,746 | 긴급 대응 | 안전비상벨(20,745) + 안심귀갓길 시설물 코드301(1,001) |
| light | 21,049 | 야간 조명 | 가로등 OA-22205(19,291) + 안심귀갓길 시설물 코드307(1,758) |
| facility | 7,637 | 정책 접근성 | 안심귀갓길 시설물 코드303~306·308 |

### 시설코드 → type 매핑 (안심귀갓길 시설물)

```python
FACILITY_CODE_MAP = {
    301: ('bell',     '안심귀갓길_안심벨'),
    302: ('cctv',     '안심귀갓길_CCTV'),
    303: ('facility', '안내표지판'),
    304: ('facility', '노면표기'),
    305: ('facility', '안심귀갓길_서비스안내판'),
    306: ('facility', '112_위치신고_안내판'),
    307: ('light',    '안심귀갓길_보안등'),
    308: ('facility', '기타'),
}
```

### 자치구 커버리지

- 자치구 정보 있는 데이터(CCTV+비상벨+시설물): **25/25 자치구** ✓
- 강동구 CCTV: 0 → 48건 (안심귀갓길 시설물 보강)
- 성동구 CCTV: 1 → 36건 (안심귀갓길 시설물 보강)
- 가로등(`type=light`): 자치구 컬럼 NA — 좌표 기반 검색에서만 사용

---

## 2. `safe_routes.parquet`

**행 수:** 362 (LineString + MultiLineString)  
**좌표계:** EPSG:4326

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `route_id` | str | 안심귀갓길 ID (예: `1111011000_04`) |
| `route_name` | str | 안심귀갓길명 (예: `종로안심04`) |
| `gu` | str | 자치구 |
| `dong` | str | 행정동 |
| `length_m` | float | 경로 길이 (미터) |
| `bell_cnt` | int | 경로 내 안심벨 개수 |
| `cctv_cnt` | int | 경로 내 CCTV 개수 |
| `light_cnt` | int | 경로 내 보안등 개수 |
| `sign_cnt` | int | 안내표지판 개수 |
| `create_year` | int | 조성 연도 |
| `detail_loc` | str | 세부 위치 설명 |
| `geometry` | LineString | EPSG:4326 |

**활용:** 입력 주소에서 가장 가까운 안심귀갓길까지의 거리 → 정책 접근성 점수

---

## 3. `kdtree_index.pkl`

**구조:** Python pickle (dict)

| 키 | 타입 | 설명 |
|---|---|---|
| `kdtree` | scipy.spatial.cKDTree | EPSG:5179 미터 좌표로 빌드된 인덱스 |
| `coords_5179` | ndarray (100670, 2) | 원본 미터 좌표 배열 |
| `crs_meters` | str | `'EPSG:5179'` |

### 사용 패턴 (Day 4)

```python
from src.preprocess import load_processed, transform_query_point

facilities, routes, idx = load_processed()
tree = idx['kdtree']

# 강남역 반경 300m 검색
x, y = transform_query_point(lat=37.4979, lon=127.0276)
nearby = tree.query_ball_point((x, y), r=300)
nearby_df = facilities.iloc[nearby]
counts = nearby_df['type'].value_counts()
```

### 검증된 성능

- 검색 시간: **0.08~0.19 ms** (3개 샘플 평균)
- 목표 < 1ms ✓

---

## 4. 검증 결과 (참고)

샘플 좌표 반경 300m 검색 결과 (검증 완료):

| 좌표 | 총 시설 | cctv | light | bell | facility |
|---|---:|---:|---:|---:|---:|
| 강남역 | 57 | 49 | 0 | 8 | 0 |
| 신촌역 | 101 | 46 | 6 | 23 | 26 |
| 잠실역 | 3 | 3 | 0 | 0 | 0 |

**잠실역 데이터 부족** → 송파구 안전비상벨 1건뿐 + 안심귀갓길 인프라 적은 영향. **알고리즘에서 거리 기반 점수로 보완 필요** (Day 4).

**강남역 light=0** → 가로등 OA-22205가 다리·대로 중심이라 강남역 근처 미커버. 알려진 한계.

---

## 5. 사용 인터페이스

Day 3 이후 모든 코드는 다음 한 줄로 데이터 로드:

```python
from src.preprocess import load_processed
facilities, routes, kdtree = load_processed()
```

새 raw 데이터가 들어오면 `02_preprocessing.ipynb`만 다시 실행하면 됨.
