"""
안전귀가Navi Day 2 전처리 모듈.

raw 폴더의 5종 공공데이터를 통합 스키마로 변환하고
KDTree 인덱스를 빌드하는 함수들.
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Optional

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree


# ─────────────────────────────────────────────────────────────────────────────
# 경로 / 상수
# ─────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent
RAW = PROJECT_ROOT / 'data' / 'raw'
PROCESSED = PROJECT_ROOT / 'data' / 'processed'

# 서울 좌표 유효 범위 (대략)
SEOUL_LAT_MIN, SEOUL_LAT_MAX = 37.4, 37.75
SEOUL_LON_MIN, SEOUL_LON_MAX = 126.7, 127.2

# 안심귀갓길 시설코드 → 점수 항목 매핑
FACILITY_CODE_MAP: dict[int, tuple[str, str]] = {
    301: ('bell', '안심귀갓길_안심벨'),
    302: ('cctv', '안심귀갓길_CCTV'),
    303: ('facility', '안내표지판'),
    304: ('facility', '노면표기'),
    305: ('facility', '안심귀갓길_서비스안내판'),
    306: ('facility', '112_위치신고_안내판'),
    307: ('light', '안심귀갓길_보안등'),
    308: ('facility', '기타'),
}

UNIFIED_COLUMNS = ['type', 'sub_type', 'lat', 'lon', 'gu', 'dong', 'source', 'extra']


# ─────────────────────────────────────────────────────────────────────────────
# 공통 유틸
# ─────────────────────────────────────────────────────────────────────────────

def _read_csv_kr(path: Path) -> pd.DataFrame:
    """한국 공공데이터 CSV — 인코딩 자동 탐색."""
    for enc in ('cp949', 'utf-8-sig', 'utf-8', 'euc-kr'):
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False)
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f'No encoding worked for {path}')


def filter_seoul_coords(df: pd.DataFrame, lat: str = 'lat', lon: str = 'lon') -> pd.DataFrame:
    """서울 좌표 범위 밖 + 결측 좌표 제거."""
    mask = (
        df[lat].between(SEOUL_LAT_MIN, SEOUL_LAT_MAX)
        & df[lon].between(SEOUL_LON_MIN, SEOUL_LON_MAX)
    )
    return df[mask].copy()


def _extract_gu(addr: pd.Series) -> pd.Series:
    return addr.astype(str).str.extract(r'서울특별시\s+([가-힣]+구)', expand=False)


def _serialize_extra(d: dict) -> str:
    """parquet 친화적인 JSON 문자열로 직렬화 (None은 빈 dict)."""
    if not d:
        return '{}'
    return json.dumps({k: v for k, v in d.items() if v is not None and pd.notna(v)},
                      ensure_ascii=False, default=str)


# ─────────────────────────────────────────────────────────────────────────────
# Loaders (raw 파일 → DataFrame)
# ─────────────────────────────────────────────────────────────────────────────

def load_raw_cctv() -> pd.DataFrame:
    path = next(RAW.glob('cct*v*seoul*.csv'))
    return _read_csv_kr(path)


def load_raw_streetlight() -> pd.DataFrame:
    return _read_csv_kr(RAW / 'streetlight_seoul.csv')


def load_raw_emergency_bell() -> pd.DataFrame:
    return _read_csv_kr(RAW / 'emergency_bell.csv')


def load_safe_route_facilities() -> gpd.GeoDataFrame:
    return gpd.read_file(RAW / 'safe_route_facilities_shp.zip')


def load_safe_routes() -> gpd.GeoDataFrame:
    return gpd.read_file(RAW / 'safe_route_path_shp.zip')


# ─────────────────────────────────────────────────────────────────────────────
# Transformers (raw → 통합 스키마)
# ─────────────────────────────────────────────────────────────────────────────

def cctv_to_unified(df: pd.DataFrame) -> pd.DataFrame:
    addr = df['소재지도로명주소'].astype(str)
    is_seoul = addr.str.startswith('서울')
    df = df[is_seoul].copy()

    out = pd.DataFrame({
        'type': 'cctv',
        'sub_type': df['설치목적구분'].fillna('미분류'),
        'lat': df['WGS84위도'],
        'lon': df['WGS84경도'],
        'gu': _extract_gu(df['소재지도로명주소']),
        'dong': pd.NA,
        'source': 'cctv_national',
    })
    out['extra'] = df.apply(
        lambda r: _serialize_extra({
            'camera_count': r.get('카메라대수'),
            'manager': r.get('관리기관명'),
            'install_date': r.get('설치연월'),
        }),
        axis=1,
    )
    return filter_seoul_coords(out).reset_index(drop=True)


def streetlight_to_unified(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({
        'type': 'light',
        'sub_type': '도로사업소·시설공단',  # 자치구 골목 가로등 미포함
        'lat': df['위도'],
        'lon': df['경도'],
        'gu': pd.NA,  # 가로등 데이터에는 자치구 정보 없음 (좌표만)
        'dong': pd.NA,
        'source': 'streetlight_seoul',
    })
    out['extra'] = df.apply(
        lambda r: _serialize_extra({'manage_id': r.get('관리번호')}),
        axis=1,
    )
    return filter_seoul_coords(out).reset_index(drop=True)


def emergency_bell_to_unified(df: pd.DataFrame) -> pd.DataFrame:
    addr = df['소재지도로명주소'].astype(str)
    is_seoul = addr.str.startswith('서울')
    df = df[is_seoul].copy()

    out = pd.DataFrame({
        'type': 'bell',
        'sub_type': df['설치장소유형'].fillna('미분류'),
        'lat': df['WGS84위도'],
        'lon': df['WGS84경도'],
        'gu': _extract_gu(df['소재지도로명주소']),
        'dong': pd.NA,
        'source': 'emergency_bell',
    })
    out['extra'] = df.apply(
        lambda r: _serialize_extra({
            'purpose': r.get('설치목적'),
            'add_func': r.get('부가기능'),
            'install_year': r.get('안전비상벨설치연도'),
        }),
        axis=1,
    )
    return filter_seoul_coords(out).reset_index(drop=True)


def facilities_to_unified(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """안심귀갓길 시설물 SHP → 통합 스키마.

    시설코드(301~308)에 따라 type/sub_type을 다르게 부여:
    - 302 CCTV → cctv 데이터에 보강
    - 301 안심벨, 307 보안등 → bell/light 보강
    - 303~306, 308 → facility (정책 접근성)
    """
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    codes = gdf['시설코드'].astype(int)
    type_subtype = codes.map(FACILITY_CODE_MAP)
    valid = type_subtype.notna()
    gdf = gdf[valid].copy()
    type_subtype = type_subtype[valid]

    types = type_subtype.apply(lambda t: t[0])
    sub_types = type_subtype.apply(lambda t: t[1])

    sigungu_clean = gdf['시군구명'].astype(str).str.replace('서울특별시 ', '', regex=False)

    out = pd.DataFrame({
        'type': types.values,
        'sub_type': sub_types.values,
        'lat': gdf.geometry.y.values,
        'lon': gdf.geometry.x.values,
        'gu': sigungu_clean.values,
        'dong': gdf['읍면동명'].values,
        'source': 'safe_route_facility',
    })
    out['extra'] = gdf.apply(
        lambda r: _serialize_extra({
            'route_id': r.get('안심귀갓길'),
            'route_name': r.get('안심귀갓_1'),
            'manager': r.get('관리기관'),
            'facility_code': int(r.get('시설코드')) if pd.notna(r.get('시설코드')) else None,
        }),
        axis=1,
    ).values
    return filter_seoul_coords(out).reset_index(drop=True)


def routes_to_unified(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """안심귀갓길 경로 SHP → 정리된 GeoDataFrame.

    SHP 컬럼명 10자 제한 때문에 잘린 컬럼들을 풀네임으로 정리.
    """
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    sigungu_clean = gdf['시군구명'].astype(str).str.replace('서울특별시 ', '', regex=False)

    out = gpd.GeoDataFrame({
        'route_id': gdf['안심귀갓_3'],
        'route_name': gdf['안심귀갓_4'],
        'gu': sigungu_clean.values,
        'dong': gdf['읍면동명'].values,
        'length_m': pd.to_numeric(gdf['길이'], errors='coerce'),
        'bell_cnt': pd.to_numeric(gdf['안심벨'], errors='coerce').fillna(0).astype(int),
        'cctv_cnt': pd.to_numeric(gdf['CCTV'], errors='coerce').fillna(0).astype(int),
        'light_cnt': pd.to_numeric(gdf['보안등'], errors='coerce').fillna(0).astype(int),
        'sign_cnt': pd.to_numeric(gdf['안심귀갓길'], errors='coerce').fillna(0).astype(int),
        'create_year': pd.to_numeric(gdf['조성년월'], errors='coerce'),
        'detail_loc': gdf['세부위치'],
        'geometry': gdf.geometry,
    }, crs='EPSG:4326')

    return out.reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# 통합 + 인덱스
# ─────────────────────────────────────────────────────────────────────────────

def build_unified_facilities() -> pd.DataFrame:
    """raw 5종 → 통합 점 데이터."""
    parts = [
        cctv_to_unified(load_raw_cctv()),
        streetlight_to_unified(load_raw_streetlight()),
        emergency_bell_to_unified(load_raw_emergency_bell()),
        facilities_to_unified(load_safe_route_facilities()),
    ]
    df = pd.concat(parts, ignore_index=True)
    df = df[UNIFIED_COLUMNS]
    return df


def build_kdtree_index(df: pd.DataFrame) -> dict:
    """좌표를 EPSG:5179(미터) 기준으로 변환 후 KDTree 빌드.

    검색 시: tree.query_ball_point((x, y), r=meters)
    """
    points_4326 = gpd.points_from_xy(df['lon'], df['lat'], crs='EPSG:4326')
    points_5179 = gpd.GeoSeries(points_4326, crs='EPSG:4326').to_crs(epsg=5179)
    coords_5179 = np.column_stack([points_5179.x, points_5179.y])

    tree = cKDTree(coords_5179)
    return {
        'kdtree': tree,
        'coords_5179': coords_5179,  # (N, 2) — KDTree 검색 좌표
        'crs_meters': 'EPSG:5179',
    }


def transform_query_point(lat: float, lon: float) -> tuple[float, float]:
    """입력 위경도 → EPSG:5179 미터 좌표 (KDTree 검색용)."""
    pt = gpd.GeoSeries([gpd.points_from_xy([lon], [lat], crs='EPSG:4326')[0]],
                       crs='EPSG:4326').to_crs(epsg=5179)
    return float(pt.iloc[0].x), float(pt.iloc[0].y)


# ─────────────────────────────────────────────────────────────────────────────
# 저장 / 로드
# ─────────────────────────────────────────────────────────────────────────────

def save_all(facilities: pd.DataFrame,
             routes: gpd.GeoDataFrame,
             kdtree_data: dict) -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)

    facilities.to_parquet(PROCESSED / 'all_facilities.parquet', index=False)
    routes.to_parquet(PROCESSED / 'safe_routes.parquet', index=False)
    with open(PROCESSED / 'kdtree_index.pkl', 'wb') as f:
        pickle.dump(kdtree_data, f)


def load_processed() -> tuple[pd.DataFrame, gpd.GeoDataFrame, dict]:
    """Day 3+ 에서 사용할 통합 로더."""
    facilities = pd.read_parquet(PROCESSED / 'all_facilities.parquet')
    routes = gpd.read_parquet(PROCESSED / 'safe_routes.parquet')
    with open(PROCESSED / 'kdtree_index.pkl', 'rb') as f:
        kdtree_data = pickle.load(f)
    return facilities, routes, kdtree_data
