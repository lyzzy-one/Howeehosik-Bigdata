"""
안전귀가Navi Day 5 AI 리포트 생성 모듈.

설계 원칙:
- LLM은 점수를 *생성*하지 않고 *해석*만 함 (점수는 scoring.py에서 이미 산출됨)
- 금지 표현 검출 시 템플릿 fallback으로 강제 전환 (안전성 우선)
- 면책 문구 항상 동봉
- API 키 없을 때도 템플릿 기반 리포트 생성 가능

데이터 흐름:
  scoring.score_signal()  →  generate_report()  →  웹 UI/API 응답
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / '.env')
OPENAI_KEY: Optional[str] = os.environ.get('OPENAI_API_KEY')

OPENAI_MODEL = 'gpt-4o-mini'
OPENAI_TIMEOUT = 15  # seconds

DISCLAIMER = (
    '본 결과는 공공데이터 기반 안전지원 인프라 분석이며, '
    '실제 범죄 발생 가능성을 예측하지 않습니다.'
)

# LLM 출력에 등장하면 즉시 템플릿 fallback으로 전환할 표현
FORBIDDEN_PATTERNS = [
    r'위험\s*(?:합니다|한\s*동네|한\s*지역|해요|함|성)',
    r'범죄\s*가능성',
    r'범죄\s*(?:이|가)\s*많',
    r'범죄율',
    r'범죄\s*발생\s*(?:가능성|할\s*수)',
    r'(?:여성|여자)\s*에게\s*위험',
    r'피해야\s*합니다',
    r'우범',
    r'슬럼',
]


# ─────────────────────────────────────────────────────────────────────────────
# 시스템·사용자 프롬프트
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """당신은 서울 1인 가구가 집을 구할 때 참고하는 '안심 주거환경 분석 리포트' 작성자입니다.

핵심 원칙 — 반드시 준수:
1. 본 서비스는 범죄 발생 가능성을 예측하지 않습니다. 대신 서울시 공공데이터 기반의 '안전지원 인프라 충분성'만 평가합니다.
2. 절대 금지 표현: "위험합니다", "범죄 가능성이 높습니다", "여성에게 위험한 동네입니다", "이 주소는 피해야 합니다", "범죄가 많이 일어날 수 있습니다", "우범", "슬럼".
3. 권장 표현: "양호합니다", "안전지원 인프라가 부족합니다", "조명 인프라가 유사 지역 평균보다 낮은 편입니다", "보완이 필요합니다", "큰길 중심의 이동이 권장됩니다".
4. 입력 JSON에 없는 사실을 추론하거나 만들어내지 마세요. 점수와 evidence(반경별 카운트, 최근접 거리)만 인용합니다.
5. 한국어, 친근하지만 정중한 톤. 4~5문장.
6. 등급(매우 양호/양호/보통/보완 필요)을 첫 문장에 자연스럽게 포함.
7. 강점 1개 + 보완점 1개를 evidence와 함께 언급.
8. 마지막에 야간 귀가 권장사항 1문장.
9. 면책 문구는 작성하지 마세요 (시스템이 자동 부착)."""


def _build_user_prompt(score_result: dict) -> str:
    import json
    addr = score_result.get('address') or '입력 주소'
    return (
        f'분석 대상 주소: {addr}\n\n'
        f'분석 결과 JSON:\n```json\n'
        f'{json.dumps(score_result, ensure_ascii=False, indent=2)}\n'
        f'```\n\n'
        f'위 JSON만 근거로 4~5문장 한국어 리포트를 작성해주세요.'
    )


# ─────────────────────────────────────────────────────────────────────────────
# 금지 표현 필터
# ─────────────────────────────────────────────────────────────────────────────

def has_forbidden(text: str) -> bool:
    return any(re.search(p, text) for p in FORBIDDEN_PATTERNS)


# ─────────────────────────────────────────────────────────────────────────────
# LLM 호출
# ─────────────────────────────────────────────────────────────────────────────

def _generate_with_llm(score_result: dict) -> Optional[str]:
    """OpenAI gpt-4o-mini로 리포트 생성. 실패/금지표현 검출 시 None."""
    if not OPENAI_KEY:
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_KEY, timeout=OPENAI_TIMEOUT)
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': _build_user_prompt(score_result)},
            ],
            temperature=0.4,
            max_tokens=400,
        )
        text = (resp.choices[0].message.content or '').strip()
    except Exception as e:
        return None

    if has_forbidden(text):
        # 1회 재시도
        try:
            resp2 = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {'role': 'system', 'content': SYSTEM_PROMPT + '\n\n이전 응답에 금지 표현이 포함되었습니다. 권장 표현만 사용해 다시 작성해주세요.'},
                    {'role': 'user', 'content': _build_user_prompt(score_result)},
                ],
                temperature=0.2,
                max_tokens=400,
            )
            text2 = (resp2.choices[0].message.content or '').strip()
            if not has_forbidden(text2):
                return text2
        except Exception:
            pass
        return None  # 재시도도 실패 → 템플릿 fallback

    return text


# ─────────────────────────────────────────────────────────────────────────────
# 템플릿 fallback (LLM 없거나 실패 시)
# ─────────────────────────────────────────────────────────────────────────────

def _generate_with_template(score_result: dict) -> str:
    total = score_result['total_score']
    grade = score_result['grade']
    summary = score_result['one_line_summary']
    action = score_result['recommended_action']

    cs = score_result['category_scores']
    actives = {k: v for k, v in cs.items() if v.get('active')}
    if not actives:
        return f'{summary} {action}'

    best_key = max(actives, key=lambda k: actives[k]['score'])
    worst_key = min(actives, key=lambda k: actives[k]['score'])
    best = actives[best_key]
    worst = actives[worst_key]

    # 강점 evidence 문장
    if best_key == 'surveillance':
        best_ev = f'반경 300m 내 CCTV {best["evidence"]["count_300m"]}개, 가장 가까운 CCTV는 {best["evidence"]["nearest_m"]:.0f}m 거리에 있습니다'
    elif best_key == 'lighting':
        best_ev = f'반경 100m 내 가로등 {best["evidence"]["count_100m"]}개로 야간 조명 접근성이 양호합니다'
    elif best_key == 'emergency':
        best_ev = f'반경 300m 내 안전비상벨 {best["evidence"]["count_300m"]}개로 긴급 대응 인프라가 잘 갖추어져 있습니다'
    elif best_key == 'safe_policy':
        best_ev = f'반경 300m 내 안심시설물 {best["evidence"]["facility_count_300m"]}개로 안심정책 인프라가 잘 갖추어져 있습니다'
    else:  # route_access
        best_ev = f'가장 가까운 안심귀갓길({best["evidence"]["nearest_route_name"]})까지 {best["evidence"]["nearest_route_m"]:.0f}m로 귀가 접근성이 양호합니다'

    # 보완점 evidence 문장
    if worst_key == 'surveillance':
        worst_ev = f'반경 300m 내 CCTV가 {worst["evidence"]["count_300m"]}개로 감시 인프라가 다소 부족한 편입니다'
    elif worst_key == 'lighting':
        worst_ev = f'반경 100m 내 가로등이 {worst["evidence"]["count_100m"]}개로 야간 조명 인프라가 보완이 필요합니다'
    elif worst_key == 'emergency':
        worst_ev = f'반경 300m 내 안전비상벨이 {worst["evidence"]["count_300m"]}개로 긴급 대응 인프라 접근성이 다소 낮은 편입니다'
    elif worst_key == 'safe_policy':
        worst_ev = f'반경 300m 내 안심시설물이 {worst["evidence"]["facility_count_300m"]}개로 안심정책 인프라가 보완이 필요한 편입니다'
    else:  # route_access
        worst_ev = f'가장 가까운 안심귀갓길까지 {worst["evidence"]["nearest_route_m"]:.0f}m로 귀가 접근성이 보완이 필요한 편입니다'

    return (
        f'이 주소의 종합 안심 주거환경 점수는 {total}점으로 {grade} 등급에 해당합니다. '
        f'{best["name"]} 항목이 {best["score"]}점으로 가장 양호하며, {best_ev}. '
        f'반면 {worst["name"]} 항목은 {worst["score"]}점으로, {worst_ev}. '
        f'{action}'
    )


# ─────────────────────────────────────────────────────────────────────────────
# 단일 진입점
# ─────────────────────────────────────────────────────────────────────────────

def generate_report(score_result: dict, prefer_llm: bool = True) -> dict:
    """점수 결과 → 자연어 리포트 (LLM 또는 템플릿).

    Returns:
      {
        'report': str,         # 본문
        'disclaimer': str,     # 면책 문구
        'source': 'llm'|'template',
        'has_forbidden': bool, # 항상 False (검출되면 템플릿으로 전환되었음)
      }
    """
    text = None
    source = 'template'

    if prefer_llm and OPENAI_KEY:
        text = _generate_with_llm(score_result)
        if text is not None:
            source = 'llm'

    if text is None:
        text = _generate_with_template(score_result)

    return {
        'report': text,
        'disclaimer': DISCLAIMER,
        'source': source,
        'has_forbidden': has_forbidden(text),  # 안전망: 템플릿도 한 번 더 검사
    }


# ─────────────────────────────────────────────────────────────────────────────
# 비교 종합 서머리 (B 기능)
# ─────────────────────────────────────────────────────────────────────────────

COMPARE_SYSTEM_PROMPT = """당신은 서울 1인 가구가 여러 매물 후보를 비교할 때 참고하는 '안심 주거환경 비교 서머리' 작성자입니다.

핵심 원칙 — 반드시 준수:
1. 본 서비스는 범죄 발생 가능성을 예측하지 않습니다. 서울시 공공데이터 기반 '안전지원 인프라 충분성'만 비교합니다.
2. 절대 금지 표현: "위험합니다", "범죄 가능성", "여성에게 위험", "피해야 합니다", "우범", "슬럼".
3. 절대 금지 — 단정적 추천: "○○를 추천합니다", "○○를 선택하세요", "○○가 가장 안전합니다". 대신 "수치 기준 가장 높은 점수", "안전지원 인프라 점수가 상위", "○○ 항목이 다른 후보보다 양호한 편" 같은 수치 기반 표현만 사용.
4. 입력 JSON에 없는 사실을 추론하거나 만들어내지 마세요. 점수와 카테고리 차이만 인용합니다.
5. 한국어, 정중한 톤, 3~4문장.
6. 첫 문장: 수치 기준 1위 후보와 그 점수.
7. 둘째~셋째 문장: 후보 간 카테고리 강약점 차이 (예: "후보 A는 감시 인프라가 상대적 상위, 후보 B는 정책 접근성이 상대적 상위").
8. 마지막 문장: 최종 결정은 사용자 본인의 우선순위·통근·예산 등을 함께 고려해야 한다는 안내.
9. 면책 문구는 작성하지 마세요 (시스템이 자동 부착)."""


def _build_compare_user_prompt(ranked: list[dict]) -> str:
    import json
    rows = []
    for i, r in enumerate(ranked, start=1):
        cs = r.get('category_scores', {})
        active = {k: v.get('score') for k, v in cs.items() if v.get('active')}
        rows.append({
            'rank': i,
            'label': r.get('label'),
            'total_score': r.get('total_score'),
            'grade': r.get('grade'),
            'category_scores': active,
        })
    return (
        f'후보 {len(ranked)}개 비교 결과 (점수 내림차순):\n```json\n'
        f'{json.dumps(rows, ensure_ascii=False, indent=2)}\n'
        f'```\n\n'
        f'위 JSON만 근거로 3~4문장 한국어 비교 서머리를 작성해주세요. '
        f'"추천" 표현은 절대 사용 금지, "수치 기준 상위" 같은 표현만 허용.'
    )


def _compare_with_llm(ranked: list[dict]) -> Optional[str]:
    if not OPENAI_KEY:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_KEY, timeout=OPENAI_TIMEOUT)
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {'role': 'system', 'content': COMPARE_SYSTEM_PROMPT},
                {'role': 'user', 'content': _build_compare_user_prompt(ranked)},
            ],
            temperature=0.3,
            max_tokens=400,
        )
        text = (resp.choices[0].message.content or '').strip()
    except Exception:
        return None

    if has_forbidden(text) or _has_recommendation(text):
        try:
            resp2 = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {'role': 'system', 'content': COMPARE_SYSTEM_PROMPT + '\n\n이전 응답이 금지 표현(위험/추천 단정)을 포함했습니다. 수치 기반 표현으로만 다시 작성하세요.'},
                    {'role': 'user', 'content': _build_compare_user_prompt(ranked)},
                ],
                temperature=0.1,
                max_tokens=400,
            )
            text2 = (resp2.choices[0].message.content or '').strip()
            if not has_forbidden(text2) and not _has_recommendation(text2):
                return text2
        except Exception:
            pass
        return None
    return text


# 추천 단정 표현 검출 (비교 서머리 전용)
_RECOMMENDATION_PATTERNS = [
    r'추천\s*(?:합니다|드립니다|해요)',
    r'선택\s*(?:하세요|하시기\s*바랍니다)',
    r'(?:권장|권유)\s*(?:합니다|드립니다)',
]


def _has_recommendation(text: str) -> bool:
    return any(re.search(p, text) for p in _RECOMMENDATION_PATTERNS)


def _compare_with_template(ranked: list[dict]) -> str:
    if len(ranked) < 2:
        return '비교 가능한 후보가 부족합니다.'
    top = ranked[0]
    bottom = ranked[-1]
    n = len(ranked)
    diff = top['total_score'] - bottom['total_score']

    # 1위와 다른 후보 사이 가장 큰 카테고리 차이
    top_cs = {k: v['score'] for k, v in top['category_scores'].items() if v.get('active')}
    diffs = []
    for r in ranked[1:]:
        rc = {k: v['score'] for k, v in r['category_scores'].items() if v.get('active')}
        for k in top_cs:
            if k in rc:
                diffs.append((k, top_cs[k] - rc[k], r.get('label')))
    biggest = max(diffs, key=lambda x: abs(x[1])) if diffs else None

    intro = (
        f'후보 {n}곳 비교 결과, 수치 기준 가장 높은 점수는 '
        f'{top.get("label")} ({top["total_score"]}점, {top["grade"]}) 입니다.'
    )
    gap = f' 1위와 최하위({bottom.get("label")}) 사이 종합 점수 차이는 {diff}점입니다.'
    detail = ''
    if biggest:
        cat_key, gap_val, other_label = biggest
        cat_name = top['category_scores'][cat_key]['name']
        if gap_val > 0:
            detail = f' 특히 {cat_name} 항목에서 {top.get("label")}이(가) {other_label}보다 {abs(gap_val)}점 높은 편입니다.'
        elif gap_val < 0:
            detail = f' 다만 {cat_name} 항목은 {other_label}이(가) {top.get("label")}보다 {abs(gap_val)}점 더 높은 편입니다.'
    closing = ' 최종 결정은 통근·예산·생활 동선 등 본인의 우선순위를 함께 고려하세요.'
    return intro + gap + detail + closing


def generate_comparison_summary(ranked: list[dict], prefer_llm: bool = True) -> dict:
    """후보별 점수 결과 리스트(정렬됨) → 비교 종합 서머리.

    Args:
        ranked: 점수 내림차순으로 이미 정렬된 score_result 리스트.
                각 항목에 'label' 필드 추가되어 있어야 함.
    """
    text = None
    source = 'template'
    if prefer_llm and OPENAI_KEY and len(ranked) >= 2:
        text = _compare_with_llm(ranked)
        if text is not None:
            source = 'llm'
    if text is None:
        text = _compare_with_template(ranked)
    return {
        'report': text,
        'disclaimer': DISCLAIMER,
        'source': source,
        'has_forbidden': has_forbidden(text) or _has_recommendation(text),
    }
