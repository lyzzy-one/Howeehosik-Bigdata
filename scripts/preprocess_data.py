"""
Data preprocessing script.

This script preprocesses all raw data files and converts them
to GeoJSON format for spatial analysis.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.preprocessor import DataPreprocessor


def main():
    """Run preprocessing for all data files."""
    print("=" * 60)
    print("안전귀가Navi 데이터 전처리")
    print("=" * 60)
    print()

    preprocessor = DataPreprocessor()

    # Run preprocessing
    results = preprocessor.preprocess_all()

    # Print results
    print("\n전처리 결과:")
    print("-" * 60)

    success_count = 0
    skip_count = 0
    error_count = 0

    for name, result in results.items():
        status = result["status"]
        if status == "success":
            print(f"✓ {name}: {result['count']}개 레코드 처리됨")
            success_count += 1
        elif status == "skipped":
            print(f"- {name}: 건너뜀 (파일 없음)")
            skip_count += 1
        else:
            print(f"✗ {name}: 오류 - {result['error']}")
            error_count += 1

    print("-" * 60)
    print(f"\n완료: 성공 {success_count}, 건너뜀 {skip_count}, 오류 {error_count}")

    if skip_count > 0:
        print("\n* 건너뛴 파일이 있습니다. 데이터 다운로드를 확인하세요:")
        print("  python scripts/download_data.py")


if __name__ == "__main__":
    main()
