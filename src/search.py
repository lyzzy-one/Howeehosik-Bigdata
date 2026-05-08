"""
안전귀가Navi Day 3 검색 모듈.

기능:
- geocode(address): 주소 → (lat, lon) — 카카오맵 REST API
- get_nearby_facilities(lat, lon, radii): 좌표 + 반경 → 시설물 카운트/거리
- nearest_per_type(lat, lon): type별 가장 가까운 시설물까지 거리
- nearest_safe_route(lat, lon): 가장 가까운 안심귀갓길 거리
- analyze_address(address): 위 모두를 묶은 단일 진입점 (Day 4 점수 엔진의 입력)
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

from preprocess import (
    PROCESSED,
    load_processed,
    transform_query_point,
)

# ─────────────────────────────────────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / '.env')

KAKAO_KEY: Optional[str] = os.environ.get('KAKAO_REST_API_KEY')
KAKAO_GEOCODE_URL = 'https://dapi.kakao.com/v2/local/search/address.json'
KAKAO_KEYWORD_URL = 'https://dapi.kakao.com/v2/local/search/keyword.json'

DEFAULT_RADII = [50, 100, 300, 500]
SCORING_TYPES = ['cctv', 'light', 'bell', 'facility']

# 모듈 로드 시 한 번만 데이터 로드 (lazy)
_FACILITIES: Optional[pd.DataFrame] = None
_ROUTES: Optional[gpd.GeoDataFrame] = None
_KDTREE_DATA: Optional[dict] = None
_ROUTES_5179: Optional[gpd.GeoDataFrame] = None  # 거리 계산용 캐시


def _ensure_loaded() -> None:
    global _FACILITIES, _ROUTES, _KDTREE_DATA, _ROUTES_5179
    if _FACILITIES is None:
        _FACILITIES, _ROUTES, _KDTREE_DATA = load_processed()
        _ROUTES_5179 = _ROUTES.to_crs(epsg=5179)


# ─────────────────────────────────────────────────────────────────────────────
# Geocoding
# ─────────────────────────────────────────────────────────────────────────────

def geocode(address: str) -> tuple[float, float]:
    """주소 → (lat, lon). 도로명/지번 둘 다 지원.

    실패 시 키워드 검색으로 fallback (예: '강남역').
    """
    if not KAKAO_KEY:
        raise RuntimeError(
            'KAKAO_REST_API_KEY 미설정. '
            f'{PROJECT_ROOT / ".env"} 파일에 KAKAO_REST_API_KEY=... 추가하세요.'
        )
    headers = {'Authorization': f'KakaoAK {KAKAO_KEY}'}

    # 1차: 주소 검색
    resp = requests.get(KAKAO_GEOCODE_URL, headers=headers,
                        params={'query': address}, timeout=5)
    resp.raise_for_status()
    docs = resp.json().get('documents', [])

    # 2차: 키워드 검색 (장소명 등)
    if not docs:
        resp = requests.get(KAKAO_KEYWORD_URL, headers=headers,
                            params={'query': address, 'size': 1}, timeout=5)
        resp.raise_for_status()
        docs = resp.json().get('documents', [])

    if not docs:
        raise ValueError(f'주소/장소를 찾을 수 없음: {address!r}')

    d = docs[0]
    return float(d['y']), float(d['x'])  # (lat, lon)


# ─────────────────────────────────────────────────────────────────────────────
# 반경 검색
# ─────────────────────────────────────────────────────────────────────────────

def get_nearby_facilities(lat: float, lon: float,
                          radii: list[int] = DEFAULT_RADII) -> dict:
    """좌표 기준 반경별 시설물 카운트.

    Returns:
      {
        'query': {'lat': ..., 'lon': ...},
        'radii': {
          50:  {'total': N, 'by_type': {'cctv': n1, 'light': n2, ...}},
          100: {...},
          ...
        }
      }
    """
    _ensure_loaded()
    x, y = transform_query_point(lat, lon)

    out = {'query': {'lat': lat, 'lon': lon}, 'radii': {}}
    for r in radii:
        idx = _KDTREE_DATA['kdtree'].query_ball_point((x, y), r=r)
        sub = _FACILITIES.iloc[idx]
        by_type = {t: int((sub['type'] == t).sum()) for t in SCORING_TYPES}
        out['radii'][r] = {
            'total': len(idx),
            'by_type': by_type,
        }
    return out


def nearest_per_type(lat: float, lon: float) -> dict:
    """type별 가장 가까운 시설물까지의 거리(m).

    송파구처럼 데이터가 적은 자치구도 0점이 나오지 않도록 거리 기반 점수에 활용.
    """
    _ensure_loaded()
    x, y = transform_query_point(lat, lon)

    out = {}
    for t in SCORING_TYPES:
        type_mask = (_FACILITIES['type'] == t).values
        if not type_mask.any():
            out[t] = None
            continue
        type_coords = _KDTREE_DATA['coords_5179'][type_mask]
        dists = np.hypot(type_coords[:, 0] - x, type_coords[:, 1] - y)
        out[t] = float(dists.min())
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 안심귀갓길 거리
# ─────────────────────────────────────────────────────────────────────────────

def nearest_safe_route(lat: float, lon: float) -> dict:
    """가장 가까운 안심귀갓길까지의 거리(m) + 경로 정보."""
    _ensure_loaded()
    from shapely.geometry import Point
    pt = gpd.GeoSeries([Point(lon, lat)], crs='EPSG:4326').to_crs(epsg=5179).iloc[0]
    distances = _ROUTES_5179.geometry.distance(pt)

    nearest = distances.idxmin()
    routes = _ROUTES.iloc[nearest]
    return {
        'distance_m': float(distances.min()),
        'route_id': str(routes['route_id']),
        'route_name': str(routes['route_name']),
        'gu': str(routes['gu']),
        'within_300m_count': int((distances < 300).sum()),
        'within_500m_count': int((distances < 500).sum()),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 통합 진입점 (Day 4 점수 엔진의 입력)
# ─────────────────────────────────────────────────────────────────────────────

def analyze_lat_lon(lat: float, lon: float,
                    radii: list[int] = DEFAULT_RADII) -> dict:
    """좌표 → 점수 계산에 필요한 모든 raw 신호 (geocoding 없이).

    Day 4 점수 엔진의 직접 입력. API 키 없을 때도 사용 가능.
    """
    return {
        'lat': lat,
        'lon': lon,
        'radii': get_nearby_facilities(lat, lon, radii)['radii'],
        'nearest_per_type': nearest_per_type(lat, lon),
        'nearest_safe_route': nearest_safe_route(lat, lon),
    }


def analyze_address(address: str,
                    radii: list[int] = DEFAULT_RADII) -> dict:
    """주소 → 점수 계산에 필요한 모든 raw 신호.

    analyze_lat_lon에 'address' 필드만 추가됨.
    """
    lat, lon = geocode(address)
    result = analyze_lat_lon(lat, lon, radii)
    result['address'] = address
    return result
