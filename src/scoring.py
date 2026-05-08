"""
안전귀가Navi Day 4 점수 엔진.

설계 원칙:
- 거리 기반 + 밀도 기반 점수의 가중 결합 (60:40)
- 데이터 적은 자치구도 거리 기반 신호로 0점 회피
- 5개 활성 카테고리: surveillance/lighting/emergency/safe_policy/route_access
- 1개 비활성 카테고리: env (시간·환경 보정)
- 가중치는 priority 옵션에 따라 동적 조정
- 모든 점수에 evidence(raw 신호) 동봉 → Day 5 AI 리포트의 근거

카테고리 가중치 (인프라 중시):
- surveillance: 30% (감시 인프라)
- lighting:     30% (야간 조명)
- emergency:    20% (긴급 대응)
- safe_policy:  10% (안심정책 - 시설물)
- route_access: 10% (귀가 접근성 - 안심귀갓길 경로)

LLM 안전성:
- recommended_action은 'ai_report_safety_rules.md'의 권장 표현만 사용
- 위험 단정/낙인 표현 금지
"""
from __future__ import annotations

from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# 카테고리 정의
# ─────────────────────────────────────────────────────────────────────────────

CATEGORIES = {
    'surveillance':  '감시 인프라',
    'lighting':      '야간 조명',
    'emergency':     '긴급 대응',
    'safe_policy':   '안심정책 접근성',
    'route_access':  '귀가 접근성',
    'env':           '시간·환경 보정',
}

ACTIVE_CATEGORIES = ['surveillance', 'lighting', 'emergency', 'safe_policy', 'route_access']
INACTIVE_CATEGORIES = {
    'env': 'MVP 미적용 — 생활인구·기상·일몰 데이터 추가 시 활성화 예정',
}

# priority별 가중치 — 활성 5개 카테고리 합 = 1.0 (인프라 중시)
PRIORITY_WEIGHTS: dict[str, dict[str, float]] = {
    'balanced':  {'surveillance': 0.30, 'lighting': 0.30, 'emergency': 0.20, 'safe_policy': 0.10, 'route_access': 0.10},
    'cctv':      {'surveillance': 0.40, 'lighting': 0.25, 'emergency': 0.15, 'safe_policy': 0.10, 'route_access': 0.10},
    'lighting':  {'surveillance': 0.25, 'lighting': 0.40, 'emergency': 0.15, 'safe_policy': 0.10, 'route_access': 0.10},
    'emergency': {'surveillance': 0.25, 'lighting': 0.25, 'emergency': 0.30, 'safe_policy': 0.10, 'route_access': 0.10},
}


# ─────────────────────────────────────────────────────────────────────────────
# 점수 빌딩 블록
# ─────────────────────────────────────────────────────────────────────────────

def _distance_score(meters: Optional[float]) -> int:
    """최근접 시설까지 거리(m) → 0~100 점수."""
    if meters is None:
        return 15
    if meters <= 50:    return 100
    if meters <= 100:   return 90
    if meters <= 200:   return 75
    if meters <= 400:   return 60
    if meters <= 600:   return 45
    if meters <= 1000:  return 30
    return 15


def _density_score(count: int, bands: list[tuple[int, int]]) -> int:
    """반경 내 시설 개수 → 0~100 점수.

    bands: [(threshold, score), ...] — count >= threshold 면 해당 score 적용.
    가장 큰 threshold부터 검사.
    """
    for threshold, score in sorted(bands, reverse=True):
        if count >= threshold:
            return score
    return 0


# 카테고리별 density 밴드 (관찰된 분포 기반)
_DENSITY_BANDS = {
    'surveillance':  [(0, 15), (1, 40), (4, 60), (10, 80), (20, 100)],  # CCTV @ 300m
    'lighting':      [(0, 15), (1, 40), (4, 60), (10, 80), (20, 100)],  # light @ 100m
    'emergency':     [(0, 15), (1, 50), (3, 75), (6, 100)],             # bell @ 300m
    'safe_policy':   [(0, 15), (1, 50), (3, 75), (5, 100)],             # facility @ 300m
    'route_access':  [(0, 20), (1, 60), (2, 80), (3, 100)],             # safe_route within 500m
}


def _blend(distance_score: int, density_score: int) -> int:
    """거리 60% + 밀도 40% 가중 블렌드 → 0~100 정수."""
    return round(0.6 * distance_score + 0.4 * density_score)


# ─────────────────────────────────────────────────────────────────────────────
# 카테고리별 점수 계산
# ─────────────────────────────────────────────────────────────────────────────

def _score_surveillance(signal: dict) -> dict:
    """감시 인프라 점수 (CCTV)."""
    nearest_m = signal['nearest_per_type'].get('cctv')
    count_300m = signal['radii'][300]['by_type']['cctv']
    count_500m = signal['radii'][500]['by_type']['cctv']

    d_score = _distance_score(nearest_m)
    den_score = _density_score(count_300m, _DENSITY_BANDS['surveillance'])
    return {
        'score': _blend(d_score, den_score),
        'components': {'distance_score': d_score, 'density_score': den_score},
        'evidence': {
            'nearest_m': nearest_m,
            'count_300m': count_300m,
            'count_500m': count_500m,
        },
    }


def _score_lighting(signal: dict) -> dict:
    """야간 조명 점수 (가로등 + 안심귀갓길 보안등)."""
    nearest_m = signal['nearest_per_type'].get('light')
    count_100m = signal['radii'][100]['by_type']['light']
    count_300m = signal['radii'][300]['by_type']['light']

    d_score = _distance_score(nearest_m)
    den_score = _density_score(count_100m, _DENSITY_BANDS['lighting'])
    return {
        'score': _blend(d_score, den_score),
        'components': {'distance_score': d_score, 'density_score': den_score},
        'evidence': {
            'nearest_m': nearest_m,
            'count_100m': count_100m,
            'count_300m': count_300m,
        },
    }


def _score_emergency(signal: dict) -> dict:
    """긴급 대응 점수 (안전비상벨 + 안심벨)."""
    nearest_m = signal['nearest_per_type'].get('bell')
    count_300m = signal['radii'][300]['by_type']['bell']
    count_500m = signal['radii'][500]['by_type']['bell']

    d_score = _distance_score(nearest_m)
    den_score = _density_score(count_300m, _DENSITY_BANDS['emergency'])
    return {
        'score': _blend(d_score, den_score),
        'components': {'distance_score': d_score, 'density_score': den_score},
        'evidence': {
            'nearest_m': nearest_m,
            'count_300m': count_300m,
            'count_500m': count_500m,
        },
    }


def _score_safe_policy(signal: dict) -> dict:
    """안심정책 접근성 점수 (안심귀갓길 시설물)."""
    facility_count_300m = signal['radii'][300]['by_type']['facility']
    facility_count_500m = signal['radii'][500]['by_type']['facility']

    # 시설물은 거리 기반 점수 대신 밀도만 사용 (시설물별 최근접 거리 데이터 없음)
    # 밀도 점수를 주로 사용하되, 존재 여부로 거리 점수 대체
    if facility_count_300m >= 1:
        d_score = 80  # 300m 내 존재
    elif facility_count_500m >= 1:
        d_score = 50  # 500m 내 존재
    else:
        d_score = 15  # 없음

    den_score = _density_score(facility_count_300m, _DENSITY_BANDS['safe_policy'])
    return {
        'score': _blend(d_score, den_score),
        'components': {'distance_score': d_score, 'density_score': den_score},
        'evidence': {
            'facility_count_300m': facility_count_300m,
            'facility_count_500m': facility_count_500m,
        },
    }


def _score_route_access(signal: dict) -> dict:
    """귀가 접근성 점수 (안심귀갓길 경로)."""
    route = signal['nearest_safe_route']
    nearest_m = route['distance_m']
    routes_within_300m = route['within_300m_count']
    routes_within_500m = route['within_500m_count']

    d_score = _distance_score(nearest_m)
    den_score = _density_score(routes_within_500m, _DENSITY_BANDS['route_access'])
    return {
        'score': _blend(d_score, den_score),
        'components': {'distance_score': d_score, 'density_score': den_score},
        'evidence': {
            'nearest_route_m': nearest_m,
            'nearest_route_name': route['route_name'],
            'nearest_route_gu': route['gu'],
            'routes_within_300m': routes_within_300m,
            'routes_within_500m': routes_within_500m,
        },
    }


_SCORERS = {
    'surveillance':  _score_surveillance,
    'lighting':      _score_lighting,
    'emergency':     _score_emergency,
    'safe_policy':   _score_safe_policy,
    'route_access':  _score_route_access,
}


# ─────────────────────────────────────────────────────────────────────────────
# 등급 / 한 줄 요약 / 추천 행동
# ─────────────────────────────────────────────────────────────────────────────

def _assign_grade(total: int) -> str:
    if total >= 80: return '매우 양호'
    if total >= 65: return '양호'
    if total >= 50: return '보통'
    return '보완 필요'


def _josa(word: str, with_batchim: str, without_batchim: str) -> str:
    """한국어 조사 받침 처리. 예: _josa('긴급 대응', '은', '는') → '은'."""
    if not word:
        return without_batchim
    last = word[-1]
    code = ord(last) - 0xAC00
    if 0 <= code < 11172 and code % 28 != 0:
        return with_batchim
    return without_batchim


def _one_line_summary(category_scores: dict, total: int, grade: str) -> str:
    """가장 강한/약한 항목 기반 한 줄 요약.

    표현 원칙: '위험'/'안전' 단정 금지. '양호/보완' 중심.
    """
    actives = {k: v['score'] for k, v in category_scores.items() if v.get('active', False)}
    if not actives:
        return f'종합 안심 점수 {total}점 ({grade}).'

    best_key = max(actives, key=actives.get)
    worst_key = min(actives, key=actives.get)
    best_name = CATEGORIES[best_key]
    worst_name = CATEGORIES[worst_key]
    best_score = actives[best_key]
    worst_score = actives[worst_key]

    if worst_score >= 70:
        return f'전반적인 안전지원 인프라가 {grade}한 주소입니다 (종합 {total}점).'
    if best_score >= 70 > worst_score:
        best_josa = _josa(best_name, '은', '는')
        worst_josa = _josa(worst_name, '은', '는')
        return f'{best_name}{best_josa} 양호하지만 {worst_name}{worst_josa} 보완이 필요한 주소입니다 (종합 {total}점).'
    return f'전반적으로 안전지원 인프라 보완이 필요한 주소입니다 (종합 {total}점).'


def _recommended_action(category_scores: dict) -> str:
    """약점 카테고리 기반 행동 권장. ai_report_safety_rules.md 표현만 사용."""
    actives = {k: v['score'] for k, v in category_scores.items() if v.get('active', False)}
    if not actives:
        return '데이터 부족으로 추천 행동을 산출하기 어렵습니다.'

    worst_key = min(actives, key=actives.get)
    worst_score = actives[worst_key]

    if worst_score >= 70:
        return '주변 안전지원 인프라가 전반적으로 양호하므로 일반적인 야간 귀가 주의사항만 따르면 됩니다.'

    tips = {
        'surveillance':  '감시 인프라가 다소 부족한 구간이므로 야간에는 안심귀갓길이나 큰길 중심의 이동이 권장됩니다.',
        'lighting':      '집 주변 조명 인프라가 상대적으로 낮게 나타나, 밤 시간대에는 조명이 많은 큰길 또는 안심귀갓길을 이용하는 것이 권장됩니다.',
        'emergency':     '긴급 대응 인프라 접근성이 보완될 여지가 있어, 가장 가까운 안전비상벨·안심지킴이집 위치를 미리 확인해두는 것이 좋습니다.',
        'safe_policy':   '안심귀갓길 시설물(안내표지판, CCTV 등)이 다소 부족한 편이므로 야간 귀가 시 주요 도로를 이용하는 것이 권장됩니다.',
        'route_access':  '안심귀갓길 접근성이 다소 낮은 편이므로 야간 귀가 시 큰길 또는 조명이 많은 경로를 우선 이용하는 것이 권장됩니다.',
    }
    return tips.get(worst_key, '야간 귀가 시 큰길 중심의 이동이 권장됩니다.')


# ─────────────────────────────────────────────────────────────────────────────
# 통합 진입점
# ─────────────────────────────────────────────────────────────────────────────

def score_signal(signal: dict, priority: str = 'balanced') -> dict:
    """analyze_lat_lon 결과 → 점수 산출 결과.

    Args:
        signal: search.analyze_lat_lon() 또는 analyze_address() 출력
        priority: 'balanced'/'cctv'/'lighting'/'emergency'/'transport' 중 하나

    Returns:
        Day 5 AI 리포트 입력으로 직접 사용 가능한 구조
    """
    if priority not in PRIORITY_WEIGHTS:
        raise ValueError(f'priority must be one of {list(PRIORITY_WEIGHTS.keys())}, got {priority!r}')
    weights = PRIORITY_WEIGHTS[priority]

    category_scores: dict[str, dict] = {}

    # 활성 카테고리: 점수 계산
    weighted_sum = 0.0
    for key in ACTIVE_CATEGORIES:
        result = _SCORERS[key](signal)
        result['active'] = True
        result['weight'] = weights[key]
        result['name'] = CATEGORIES[key]
        category_scores[key] = result
        weighted_sum += result['score'] * weights[key]

    total_score = round(weighted_sum)
    grade = _assign_grade(total_score)

    # 비활성 카테고리: placeholder
    for key, note in INACTIVE_CATEGORIES.items():
        category_scores[key] = {
            'name': CATEGORIES[key],
            'score': None,
            'weight': 0.0,
            'active': False,
            'note': note,
        }

    return {
        'lat': signal.get('lat'),
        'lon': signal.get('lon'),
        'address': signal.get('address'),
        'priority': priority,
        'total_score': total_score,
        'grade': grade,
        'one_line_summary': _one_line_summary(category_scores, total_score, grade),
        'recommended_action': _recommended_action(category_scores),
        'category_scores': category_scores,
    }
