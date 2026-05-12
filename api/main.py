"""
안전귀가Navi FastAPI 백엔드.

기동:
    cd api
    uvicorn main:app --reload --port 8000
"""
from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator

# src 모듈 import
SRC = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(SRC))

import search  # noqa: E402
import scoring  # noqa: E402
import report  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# 서울 경계 (대략적 bounding box)
# ─────────────────────────────────────────────────────────────────────────────
SEOUL_LAT_MIN, SEOUL_LAT_MAX = 37.42, 37.72
SEOUL_LON_MIN, SEOUL_LON_MAX = 126.76, 127.20


def _in_seoul(lat: float, lon: float) -> bool:
    return (SEOUL_LAT_MIN <= lat <= SEOUL_LAT_MAX
            and SEOUL_LON_MIN <= lon <= SEOUL_LON_MAX)


# ─────────────────────────────────────────────────────────────────────────────
# 요청·응답 스키마
# ─────────────────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    address: str = Field(..., description='서울 도로명/지번 주소 또는 장소명')
    priority: str = Field('balanced', description='balanced/cctv/lighting/emergency/transport')


class AnalyzeCoordRequest(BaseModel):
    lat: float
    lon: float
    priority: str = 'balanced'


class Candidate(BaseModel):
    label: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None

    @model_validator(mode='after')
    def _has_address_or_coord(self):
        has_addr = bool(self.address and self.address.strip())
        has_coord = self.lat is not None and self.lon is not None
        if not has_addr and not has_coord:
            raise ValueError('각 후보는 address 또는 (lat, lon) 중 하나는 필수입니다')
        return self


class CompareRequest(BaseModel):
    candidates: list[Candidate] = Field(..., min_length=2, max_length=5)
    priority: str = Field('balanced')


# ─────────────────────────────────────────────────────────────────────────────
# 데이터 워밍업 (첫 요청 지연 방지)
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 preprocess 데이터 로드
    print('[startup] 데이터 로드 중...')
    search._ensure_loaded()
    print(f'[startup] facilities {len(search._FACILITIES):,}건, '
          f'routes {len(search._ROUTES):,}건 로드 완료')
    print(f'[startup] KAKAO_KEY: {bool(search.KAKAO_KEY)}, '
          f'OPENAI_KEY: {bool(report.OPENAI_KEY)}')
    yield


# ─────────────────────────────────────────────────────────────────────────────
# 앱
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title='안전귀가Navi API',
    description='서울 1인 가구 안심 주거환경 스코어링',
    version='0.1.0',
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000', 'http://127.0.0.1:3000'],
    allow_origin_regex=r'https://.*\.vercel\.app',
    allow_methods=['*'],
    allow_headers=['*'],
)


# ─────────────────────────────────────────────────────────────────────────────
# 엔드포인트
# ─────────────────────────────────────────────────────────────────────────────

@app.get('/api/health')
def health():
    return {
        'status': 'ok',
        'kakao_key_set': bool(search.KAKAO_KEY),
        'openai_key_set': bool(report.OPENAI_KEY),
        'data_loaded': search._FACILITIES is not None,
    }


@app.post('/api/analyze')
def analyze(req: AnalyzeRequest):
    """주소 → 안심 주거환경 분석. 카카오 API 키 필요."""
    try:
        signal = search.analyze_address(req.address)
    except RuntimeError as e:  # API 키 미설정
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:    # 주소 못 찾음
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:     # 네트워크/카카오 에러 등
        raise HTTPException(status_code=502, detail=f'Geocoding 실패: {e}')

    return _build_response(signal, req.priority)


@app.post('/api/analyze-coord')
def analyze_coord(req: AnalyzeCoordRequest):
    """좌표 → 안심 주거환경 분석. API 키 없이 동작."""
    signal = search.analyze_lat_lon(req.lat, req.lon)
    signal['address'] = f'좌표 ({req.lat:.4f}, {req.lon:.4f})'
    return _build_response(signal, req.priority)


def _build_response(signal: dict, priority: str) -> dict:
    if priority not in scoring.PRIORITY_WEIGHTS:
        raise HTTPException(status_code=400,
                            detail=f'priority must be one of {list(scoring.PRIORITY_WEIGHTS.keys())}')

    score = scoring.score_signal(signal, priority=priority)
    rep = report.generate_report(score)

    return {
        **score,
        'ai_report': rep['report'],
        'disclaimer': rep['disclaimer'],
        'report_source': rep['source'],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 후보 비교 (B 기능)
# ─────────────────────────────────────────────────────────────────────────────

def _default_label(idx: int) -> str:
    return f'후보 {chr(ord("A") + idx)}'


async def _resolve_coord(cand: Candidate) -> tuple[float, float]:
    """주소 우선이면 geocoding, 좌표 있으면 그대로."""
    if cand.lat is not None and cand.lon is not None:
        return cand.lat, cand.lon
    return await asyncio.to_thread(search.geocode, cand.address)


@app.post('/api/compare')
async def compare(req: CompareRequest):
    """후보 2~5개 안전도 비교. 점수 내림차순 정렬, 동점은 emergency 효명."""
    if req.priority not in scoring.PRIORITY_WEIGHTS:
        raise HTTPException(status_code=400,
                            detail=f'priority must be one of {list(scoring.PRIORITY_WEIGHTS.keys())}')

    # 1. 라벨 자동 부여
    cands = []
    for i, c in enumerate(req.candidates):
        label = (c.label or '').strip() or _default_label(i)
        cands.append({'idx': i, 'label': label, 'src': c})

    # 2. 좌표 해석 (병렬). 실패는 errors에 모음.
    async def _resolve(item):
        try:
            lat, lon = await _resolve_coord(item['src'])
            return {'ok': True, 'item': item, 'lat': lat, 'lon': lon}
        except RuntimeError as e:  # 카카오 키 미설정
            return {'ok': False, 'item': item, 'error': str(e), 'status': 503}
        except ValueError as e:    # 주소 못 찾음
            return {'ok': False, 'item': item, 'error': str(e), 'status': 404}
        except Exception as e:
            return {'ok': False, 'item': item, 'error': f'좌표 해석 실패: {e}', 'status': 502}

    resolved = await asyncio.gather(*[_resolve(c) for c in cands])

    errors = []
    succeeded = []
    for r in resolved:
        if r['ok']:
            succeeded.append(r)
        else:
            src = r['item']['src']
            errors.append({
                'label': r['item']['label'],
                'input': {
                    'address': src.address,
                    'lat': src.lat,
                    'lon': src.lon,
                },
                'error': r['error'],
            })

    # 3. 중복 좌표 제거 (소수점 6자리 기준 ≈ 11cm)
    seen: dict[tuple, dict] = {}
    warnings: list[str] = []
    deduped: list[dict] = []
    for r in succeeded:
        key = (round(r['lat'], 6), round(r['lon'], 6))
        if key in seen:
            warnings.append(
                f'{r["item"]["label"]}: {seen[key]["item"]["label"]}과 동일 좌표여서 중복 제거되었습니다'
            )
            continue
        seen[key] = r
        deduped.append(r)

    # 4. 서울 경계 체크 (경고만, 분석은 진행)
    for r in deduped:
        if not _in_seoul(r['lat'], r['lon']):
            warnings.append(
                f'{r["item"]["label"]}: 서울 외 좌표({r["lat"]:.4f}, {r["lon"]:.4f})로 점수 신뢰도가 낮습니다'
            )

    if len(deduped) < 2:
        # 비교 자체가 불가
        return {
            'priority': req.priority,
            'ranked': [],
            'errors': errors,
            'warnings': warnings,
            'summary': None,
            'message': '비교 가능한 후보가 2개 미만입니다',
        }

    # 5. 좌표별 analyze + score (CPU/IO 혼합 → to_thread 병렬)
    async def _analyze_and_score(r):
        signal = await asyncio.to_thread(search.analyze_lat_lon, r['lat'], r['lon'])
        # 라벨이 곧 식별자. address가 입력이면 보존, 아니면 좌표 표기.
        signal['address'] = (
            r['item']['src'].address
            if r['item']['src'].address
            else f'좌표 ({r["lat"]:.4f}, {r["lon"]:.4f})'
        )
        score = await asyncio.to_thread(scoring.score_signal, signal, req.priority)
        score['label'] = r['item']['label']
        score['out_of_seoul'] = not _in_seoul(r['lat'], r['lon'])
        return score

    scored = await asyncio.gather(*[_analyze_and_score(r) for r in deduped])

    # 6. 정렬: total_score desc, 동점이면 emergency desc
    def _emergency_score(s):
        cs = s.get('category_scores', {}).get('emergency', {})
        return cs.get('score') or 0

    scored.sort(key=lambda s: (-s['total_score'], -_emergency_score(s)))

    # 7. 후보별 개별 리포트 + 비교 종합 서머리 병렬
    individual_reports_task = asyncio.gather(
        *[asyncio.to_thread(report.generate_report, s) for s in scored]
    )
    summary_task = asyncio.to_thread(report.generate_comparison_summary, scored)
    individual_reports, summary = await asyncio.gather(
        individual_reports_task, summary_task,
    )

    # 8. 응답 조립
    ranked = []
    for rank, (s, rep) in enumerate(zip(scored, individual_reports), start=1):
        ranked.append({
            **s,
            'rank': rank,
            'is_top': rank == 1,
            'ai_report': rep['report'],
            'report_source': rep['source'],
        })

    return {
        'priority': req.priority,
        'ranked': ranked,
        'errors': errors,
        'warnings': warnings,
        'summary': {
            'report': summary['report'],
            'disclaimer': summary['disclaimer'],
            'source': summary['source'],
        },
    }
