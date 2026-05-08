"""Safety score calculation endpoint."""
from fastapi import APIRouter, HTTPException

from src.models.request import SafetyScoreRequest
from src.models.response import SafetyScoreResponse, ErrorResponse
from src.core.scoring.calculator import SafetyScoreCalculator
from src.core.spatial.geocoder import KakaoGeocoder
from src.config import get_settings

router = APIRouter()
settings = get_settings()


@router.post(
    "/safety-score",
    response_model=SafetyScoreResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def calculate_safety_score(request: SafetyScoreRequest):
    """
    Calculate safety score for a given address.

    - **address**: 서울시 내 주소 (예: 서울특별시 관악구 신림동 123-45)

    Returns:
    - 총점 및 등급
    - 카테고리별 점수
    - 분석 근거 (evidence)
    - AI 리포트
    """
    try:
        # 1. 주소 → 좌표 변환
        geocoder = KakaoGeocoder()
        coords = await geocoder.geocode(request.address)

        if not coords:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INVALID_ADDRESS",
                    "message": "주소를 찾을 수 없습니다. 정확한 주소를 입력해주세요."
                }
            )

        # 서울시 범위 확인
        if not geocoder.is_in_seoul(coords["lat"], coords["lng"]):
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "OUT_OF_COVERAGE",
                    "message": "현재 서비스는 서울시 지역만 지원합니다."
                }
            )

        # 2. 안전 점수 계산
        calculator = SafetyScoreCalculator()
        result = await calculator.calculate(
            lat=coords["lat"],
            lng=coords["lng"],
            address=request.address
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": f"점수 계산 중 오류가 발생했습니다: {str(e)}"
            }
        )
