"""
Data download script.

This script provides instructions and utilities for downloading
the required datasets for the 안전귀가Navi service.

Note: Most datasets require manual download from the data portals.
This script helps organize and verify the downloaded files.
"""
import os
from pathlib import Path


# Data sources information
DATA_SOURCES = {
    "cctv_seoul.csv": {
        "name": "전국 CCTV 표준데이터 (서울)",
        "url": "https://www.data.go.kr/data/15013094/standard.do",
        "description": "전국 CCTV 데이터에서 서울시 데이터만 추출",
        "required_columns": ["위도", "경도"]
    },
    "streetlight.csv": {
        "name": "서울시 가로등 위치 정보",
        "url": "https://data.seoul.go.kr/dataList/OA-22205/F/1/datasetView.do",
        "description": "서울시 가로등 위치 데이터",
        "required_columns": ["위도", "경도"]
    },
    "walklight.csv": {
        "name": "서울특별시 보행등 위도경도 현황",
        "url": "https://www.data.go.kr/data/15124273/fileData.do",
        "description": "서울시 보행등 위치 데이터",
        "required_columns": ["위도", "경도"]
    },
    "emergency_bell.csv": {
        "name": "행정안전부 안전비상벨 위치정보",
        "url": "https://www.data.go.kr/data/15075539/fileData.do",
        "description": "안전비상벨 위치 데이터 (서울시 필터링 필요)",
        "required_columns": ["위도", "경도"]
    },
    "safe_facility.csv": {
        "name": "서울시 안심귀갓길 안전시설물",
        "url": "https://data.seoul.go.kr/dataList/OA-21696/S/1/datasetView.do",
        "description": "안심귀갓길 내 안전시설물 데이터",
        "required_columns": ["위도", "경도"]
    },
    "safe_route.csv": {
        "name": "서울시 안심귀갓길 경로",
        "url": "https://data.seoul.go.kr/dataList/OA-21695/S/1/datasetView.do",
        "description": "안심귀갓길 경로 데이터 (LineString)",
        "required_columns": ["경로좌표 또는 geometry"]
    }
}


def check_data_files():
    """Check which data files exist."""
    raw_path = Path("data/raw")

    print("=" * 60)
    print("안전귀가Navi 데이터 파일 체크")
    print("=" * 60)
    print()

    missing = []
    found = []

    for filename, info in DATA_SOURCES.items():
        filepath = raw_path / filename
        if filepath.exists():
            size = filepath.stat().st_size / 1024  # KB
            found.append((filename, size))
            print(f"✓ {filename} ({size:.1f} KB)")
        else:
            missing.append((filename, info))
            print(f"✗ {filename} - 다운로드 필요")

    print()
    print("-" * 60)

    if missing:
        print(f"\n다운로드가 필요한 파일: {len(missing)}개\n")
        for filename, info in missing:
            print(f"파일: {filename}")
            print(f"  이름: {info['name']}")
            print(f"  URL: {info['url']}")
            print(f"  설명: {info['description']}")
            print()
    else:
        print("\n모든 데이터 파일이 준비되었습니다!")

    return len(missing) == 0


def print_download_guide():
    """Print detailed download guide."""
    print("""
================================================================================
데이터 다운로드 가이드
================================================================================

1. 전국 CCTV 표준데이터
   - URL: https://www.data.go.kr/data/15013094/standard.do
   - 다운로드 후 서울시 데이터만 필터링
   - 저장: data/raw/cctv_seoul.csv

2. 서울시 가로등 위치 정보
   - URL: https://data.seoul.go.kr/dataList/OA-22205/F/1/datasetView.do
   - CSV 다운로드
   - 저장: data/raw/streetlight.csv

3. 서울특별시 보행등 위도경도 현황
   - URL: https://www.data.go.kr/data/15124273/fileData.do
   - 파일 다운로드
   - 저장: data/raw/walklight.csv

4. 행정안전부 안전비상벨 위치정보
   - URL: https://www.data.go.kr/data/15075539/fileData.do
   - 파일 다운로드 (전국 데이터, 전처리 시 서울 필터링)
   - 저장: data/raw/emergency_bell.csv

5. 서울시 안심귀갓길 안전시설물
   - URL: https://data.seoul.go.kr/dataList/OA-21696/S/1/datasetView.do
   - CSV 다운로드
   - 저장: data/raw/safe_facility.csv

6. 서울시 안심귀갓길 경로
   - URL: https://data.seoul.go.kr/dataList/OA-21695/S/1/datasetView.do
   - CSV 다운로드
   - 저장: data/raw/safe_route.csv

================================================================================
다운로드 완료 후 다음 명령어로 전처리를 실행하세요:
    python scripts/preprocess_data.py
================================================================================
""")


if __name__ == "__main__":
    import sys

    # Create data directories if they don't exist
    Path("data/raw").mkdir(parents=True, exist_ok=True)
    Path("data/processed").mkdir(parents=True, exist_ok=True)

    if "--guide" in sys.argv:
        print_download_guide()
    else:
        all_ready = check_data_files()
        if not all_ready:
            print("\n자세한 다운로드 가이드: python scripts/download_data.py --guide")
