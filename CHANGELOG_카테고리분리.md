# 변경 사항 정리: 카테고리 5개 분리

**변경일**: 2026-05-08
**커밋**: `refactor: 카테고리 5개로 분리 (policy → safe_policy + route_access)`

---

## 1. 변경 개요

기존 4개 카테고리 구조에서 `policy`를 2개로 분리하여 **5개 카테고리 구조**로 변경

| 변경 전 (4개) | 변경 후 (5개) |
|---------------|---------------|
| surveillance (30%) | surveillance (30%) |
| lighting (25%) | lighting (30%) |
| emergency (25%) | emergency (20%) |
| policy (20%) | **safe_policy (10%)** |
| - | **route_access (10%)** |

---

## 2. 변경 이유

### 기존 문제점
- `policy` 카테고리가 **시설물**과 **경로** 두 가지를 혼합하여 계산
- 시설물은 많지만 귀갓길이 먼 경우, 점수가 평균으로 상쇄됨
- 세부 분석 정보 제공이 어려움

### 변경 후 장점
- **시설물**(안내표지판, CCTV 등)과 **경로**(안심귀갓길)를 분리하여 개별 점수 확인 가능
- 사용자에게 더 상세한 정보 제공 가능
- 가중치 개별 조정 가능

---

## 3. 수정 파일 및 상세 내용

### 3.1 `src/scoring.py`

#### 카테고리 정의 변경

```python
# 변경 전
CATEGORIES = {
    'surveillance':  '감시 인프라',
    'lighting':      '야간 조명',
    'emergency':     '긴급 대응',
    'policy':        '정책 접근성',      # 삭제
    'transport':     '귀가 접근성',      # 삭제
    'env':           '시간·환경 보정',
}

# 변경 후
CATEGORIES = {
    'surveillance':  '감시 인프라',
    'lighting':      '야간 조명',
    'emergency':     '긴급 대응',
    'safe_policy':   '안심정책 접근성',  # 신규
    'route_access':  '귀가 접근성',      # 신규
    'env':           '시간·환경 보정',
}
```

#### 활성 카테고리 변경

```python
# 변경 전
ACTIVE_CATEGORIES = ['surveillance', 'lighting', 'emergency', 'policy']

# 변경 후
ACTIVE_CATEGORIES = ['surveillance', 'lighting', 'emergency', 'safe_policy', 'route_access']
```

#### 가중치 변경 (balanced 기준)

```python
# 변경 전
'balanced': {'surveillance': 0.30, 'lighting': 0.25, 'emergency': 0.25, 'policy': 0.20}

# 변경 후
'balanced': {'surveillance': 0.30, 'lighting': 0.30, 'emergency': 0.20, 'safe_policy': 0.10, 'route_access': 0.10}
```

#### 스코어링 함수 분리

**변경 전**: `_score_policy()` 하나로 통합

```python
def _score_policy(signal: dict) -> dict:
    """정책 접근성 점수 (안심귀갓길 경로 + 시설물)."""
    route = signal['nearest_safe_route']
    nearest_m = route['distance_m']
    routes_within_500m = route['within_500m_count']
    facility_count_300m = signal['radii'][300]['by_type']['facility']
    # ... 하나의 점수로 계산
```

**변경 후**: 2개 함수로 분리

```python
def _score_safe_policy(signal: dict) -> dict:
    """안심정책 접근성 점수 (안심귀갓길 시설물)."""
    facility_count_300m = signal['radii'][300]['by_type']['facility']
    facility_count_500m = signal['radii'][500]['by_type']['facility']

    # 시설물 존재 여부로 거리 점수 대체
    if facility_count_300m >= 1:
        d_score = 80   # 300m 내 존재
    elif facility_count_500m >= 1:
        d_score = 50   # 500m 내 존재
    else:
        d_score = 15   # 없음
    # ...

def _score_route_access(signal: dict) -> dict:
    """귀가 접근성 점수 (안심귀갓길 경로)."""
    route = signal['nearest_safe_route']
    nearest_m = route['distance_m']
    routes_within_300m = route['within_300m_count']
    routes_within_500m = route['within_500m_count']
    # ...
```

#### 권장 행동 메시지 추가

```python
tips = {
    'surveillance':  '감시 인프라가 다소 부족한 구간이므로...',
    'lighting':      '집 주변 조명 인프라가 상대적으로 낮게 나타나...',
    'emergency':     '긴급 대응 인프라 접근성이 보완될 여지가 있어...',
    'safe_policy':   '안심귀갓길 시설물(안내표지판, CCTV 등)이 다소 부족한 편이므로...',  # 신규
    'route_access':  '안심귀갓길 접근성이 다소 낮은 편이므로...',  # 신규
}
```

---

### 3.2 `src/report.py`

#### 템플릿 fallback 문장 추가

**강점 evidence 문장 추가**:
```python
elif best_key == 'safe_policy':
    best_ev = f'반경 300m 내 안심시설물 {best["evidence"]["facility_count_300m"]}개로 안심정책 인프라가 잘 갖추어져 있습니다'
else:  # route_access
    best_ev = f'가장 가까운 안심귀갓길({best["evidence"]["nearest_route_name"]})까지 {best["evidence"]["nearest_route_m"]:.0f}m로 귀가 접근성이 양호합니다'
```

**보완점 evidence 문장 추가**:
```python
elif worst_key == 'safe_policy':
    worst_ev = f'반경 300m 내 안심시설물이 {worst["evidence"]["facility_count_300m"]}개로 안심정책 인프라가 보완이 필요한 편입니다'
else:  # route_access
    worst_ev = f'가장 가까운 안심귀갓길까지 {worst["evidence"]["nearest_route_m"]:.0f}m로 귀가 접근성이 보완이 필요한 편입니다'
```

---

## 4. API 응답 변경 예시

### 변경 전

```json
{
  "category_scores": {
    "surveillance": { "score": 78, "name": "감시 인프라" },
    "lighting": { "score": 65, "name": "야간 조명" },
    "emergency": { "score": 72, "name": "긴급 대응" },
    "policy": { "score": 58, "name": "정책 접근성" }
  }
}
```

### 변경 후

```json
{
  "category_scores": {
    "surveillance": { "score": 78, "name": "감시 인프라" },
    "lighting": { "score": 65, "name": "야간 조명" },
    "emergency": { "score": 72, "name": "긴급 대응" },
    "safe_policy": { "score": 45, "name": "안심정책 접근성" },
    "route_access": { "score": 71, "name": "귀가 접근성" }
  }
}
```

---

## 5. 가중치 전체 비교표

| 카테고리 | 변경 전 | 변경 후 | 비고 |
|----------|---------|---------|------|
| surveillance | 30% | **30%** | 유지 |
| lighting | 25% | **30%** | +5% |
| emergency | 25% | **20%** | -5% |
| policy | 20% | - | 삭제 (분리) |
| safe_policy | - | **10%** | 신규 |
| route_access | - | **10%** | 신규 |
| **합계** | 100% | 100% | |

---

## 6. 주의사항

1. **프론트엔드 수정 필요**: `policy` → `safe_policy`, `route_access`로 키 변경됨
2. **테스트 코드 수정 필요**: 카테고리 관련 테스트가 있다면 업데이트 필요
3. **기존 캐시 데이터**: 기존 응답 캐시가 있다면 갱신 필요

---

## 7. 관련 커밋

```
커밋 해시: 8ee5dc1
브랜치: main
메시지: refactor: 카테고리 5개로 분리 (policy → safe_policy + route_access)
```
