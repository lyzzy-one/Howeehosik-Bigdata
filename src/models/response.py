"""Response models."""
from typing import Optional
from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    """Coordinate model."""
    lat: float
    lng: float


class CategoryScore(BaseModel):
    """Category score model."""
    score: float = Field(..., description="획득 점수")
    max: float = Field(..., description="최대 점수")
    percentage: int = Field(..., description="백분율 (0-100)")


class CategoryScores(BaseModel):
    """All category scores."""
    surveillance: CategoryScore = Field(..., description="감시 인프라 점수")
    lighting: CategoryScore = Field(..., description="야간 조명 점수")
    emergency: CategoryScore = Field(..., description="긴급 대응 점수")
    safe_policy: CategoryScore = Field(..., description="안심정책 접근성 점수")
    route_access: CategoryScore = Field(..., description="귀가 접근성 점수")


class Evidence(BaseModel):
    """Evidence data model."""
    # CCTV
    cctv_100m_count: int = Field(0, description="100m 반경 CCTV 수")
    cctv_300m_count: int = Field(0, description="300m 반경 CCTV 수")
    nearest_cctv_distance_m: Optional[float] = Field(None, description="가장 가까운 CCTV 거리(m)")

    # Streetlight
    streetlight_50m_count: int = Field(0, description="50m 반경 가로등 수")
    streetlight_100m_count: int = Field(0, description="100m 반경 가로등 수")
    walklight_100m_count: int = Field(0, description="100m 반경 보행등 수")

    # Emergency Bell
    emergencybell_300m_count: int = Field(0, description="300m 반경 비상벨 수")
    nearest_emergencybell_distance_m: Optional[float] = Field(None, description="가장 가까운 비상벨 거리(m)")

    # Safe Facility
    safe_facility_300m_count: int = Field(0, description="300m 반경 안심시설물 수")

    # Safe Route
    nearest_safe_route_distance_m: Optional[float] = Field(None, description="가장 가까운 안심귀갓길 거리(m)")
    safe_route_exists_500m: bool = Field(False, description="500m 내 안심귀갓길 존재 여부")


class SafetyScoreData(BaseModel):
    """Safety score data model."""
    address: str
    coordinates: Coordinates
    total_score: int = Field(..., ge=0, le=100, description="총점 (0-100)")
    grade: str = Field(..., description="등급")
    category_scores: CategoryScores
    evidence: Evidence
    ai_report: str = Field(..., description="AI 생성 리포트")


class SafetyScoreResponse(BaseModel):
    """Response model for safety score."""
    success: bool = True
    data: SafetyScoreData


class ErrorDetail(BaseModel):
    """Error detail model."""
    code: str
    message: str


class ErrorResponse(BaseModel):
    """Error response model."""
    success: bool = False
    error: ErrorDetail
