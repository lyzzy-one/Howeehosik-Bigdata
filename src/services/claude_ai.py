"""Claude AI report generation service."""
from typing import Dict, Any
import anthropic

from src.config import get_settings
from src.models.response import CategoryScore


class ClaudeReportGenerator:
    """Generate safety analysis reports using Claude API."""

    SYSTEM_PROMPT = """당신은 서울시 주거 환경 안전 분석 전문가입니다.
사용자에게 특정 주소의 안전 인프라 현황을 분석하여 보고서를 작성합니다.

중요 원칙:
1. 절대로 "범죄 가능성", "위험 지역", "범죄 발생" 같은 표현을 사용하지 마세요.
2. 대신 "안전지원 인프라 수준", "야간 조명 환경", "귀가 지원성" 위주로 설명하세요.
3. 객관적인 데이터 기반으로 설명하되, 긍정적이고 건설적인 톤을 유지하세요.
4. 개선이 필요한 부분은 "~가 부족합니다" 대신 "~를 추가로 확인하시는 것을 권장드립니다" 형태로 표현하세요.

리포트 형식:
- 2-3문장의 간결한 요약
- 주요 강점 1-2개 언급
- 참고사항 또는 권장사항 1개 (필요시)
"""

    def __init__(self):
        self.settings = get_settings()
        self.client = None

        if self.settings.anthropic_api_key:
            self.client = anthropic.Anthropic(
                api_key=self.settings.anthropic_api_key
            )

    async def generate_report(
        self,
        address: str,
        total_score: int,
        grade: str,
        category_scores: Dict[str, CategoryScore],
        evidence: Dict[str, Any]
    ) -> str:
        """
        Generate AI safety report.

        Args:
            address: Address string
            total_score: Total safety score (0-100)
            grade: Grade string
            category_scores: Category scores dict
            evidence: Raw evidence data dict

        Returns:
            Generated report string
        """
        if not self.client:
            return self._generate_fallback_report(
                address, total_score, grade, category_scores, evidence
            )

        try:
            user_prompt = self._build_prompt(
                address, total_score, grade, category_scores, evidence
            )

            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                system=self.SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            return message.content[0].text

        except Exception as e:
            # Fallback to template-based report
            return self._generate_fallback_report(
                address, total_score, grade, category_scores, evidence
            )

    def _build_prompt(
        self,
        address: str,
        total_score: int,
        grade: str,
        category_scores: Dict[str, CategoryScore],
        evidence: Dict[str, Any]
    ) -> str:
        """Build prompt for Claude API."""
        return f"""다음 주소의 안전 인프라 분석 결과를 바탕으로 간결한 리포트를 작성해주세요.

주소: {address}
총점: {total_score}점 (등급: {grade})

카테고리별 점수:
- 감시 인프라: {category_scores['surveillance'].percentage}% ({category_scores['surveillance'].score}/{category_scores['surveillance'].max}점)
- 야간 조명: {category_scores['lighting'].percentage}% ({category_scores['lighting'].score}/{category_scores['lighting'].max}점)
- 긴급 대응: {category_scores['emergency'].percentage}% ({category_scores['emergency'].score}/{category_scores['emergency'].max}점)
- 안심정책 접근성: {category_scores['safe_policy'].percentage}% ({category_scores['safe_policy'].score}/{category_scores['safe_policy'].max}점)
- 귀가 접근성: {category_scores['route_access'].percentage}% ({category_scores['route_access'].score}/{category_scores['route_access'].max}점)

상세 데이터:
- 100m 내 CCTV: {evidence['cctv_100m_count']}대
- 300m 내 CCTV: {evidence['cctv_300m_count']}대
- 가장 가까운 CCTV: {evidence['nearest_cctv_distance_m']}m
- 50m 내 가로등: {evidence['streetlight_50m_count']}개
- 100m 내 가로등: {evidence['streetlight_100m_count']}개
- 100m 내 보행등: {evidence['walklight_100m_count']}개
- 300m 내 비상벨: {evidence['emergencybell_300m_count']}개
- 가장 가까운 비상벨: {evidence['nearest_emergencybell_distance_m']}m
- 300m 내 안심시설물: {evidence['safe_facility_300m_count']}개
- 가장 가까운 안심귀갓길: {evidence['nearest_safe_route_distance_m']}m
- 500m 내 안심귀갓길 존재: {'예' if evidence['safe_route_exists_500m'] else '아니오'}

위 데이터를 바탕으로 2-3문장의 리포트를 작성해주세요."""

    def _generate_fallback_report(
        self,
        address: str,
        total_score: int,
        grade: str,
        category_scores: Dict[str, CategoryScore],
        evidence: Dict[str, Any]
    ) -> str:
        """Generate template-based fallback report."""
        # Determine strengths and weaknesses
        scores = {
            "감시 인프라": category_scores["surveillance"].percentage,
            "야간 조명": category_scores["lighting"].percentage,
            "긴급 대응": category_scores["emergency"].percentage,
            "안심정책": category_scores["safe_policy"].percentage,
            "귀가 접근성": category_scores["route_access"].percentage
        }

        strengths = [k for k, v in scores.items() if v >= 70]
        improvements = [k for k, v in scores.items() if v < 50]

        # Build report
        report_parts = []

        # Overall assessment
        if total_score >= 70:
            report_parts.append(
                f"이 주소는 전반적으로 {grade}한 안전 인프라 환경을 갖추고 있습니다."
            )
        elif total_score >= 55:
            report_parts.append(
                f"이 주소는 기본적인 안전 인프라가 갖춰진 지역입니다."
            )
        else:
            report_parts.append(
                f"이 주소 주변의 안전 인프라 현황을 확인해 보았습니다."
            )

        # Strengths
        if strengths:
            if "감시 인프라" in strengths:
                report_parts.append(
                    f"반경 100m 내에 CCTV {evidence['cctv_100m_count']}대가 "
                    f"설치되어 있어 감시 환경이 양호합니다."
                )
            elif "야간 조명" in strengths:
                report_parts.append(
                    f"50m 내 가로등 {evidence['streetlight_50m_count']}개, "
                    f"100m 내 보행등 {evidence['walklight_100m_count']}개가 확인되어 "
                    f"야간 조명 환경이 양호합니다."
                )

        # Recommendations
        if improvements:
            if "야간 조명" in improvements:
                report_parts.append(
                    "야간 귀가 시에는 큰 도로를 이용하시는 것을 권장드립니다."
                )
            elif "긴급 대응" in improvements:
                report_parts.append(
                    "주변 안전비상벨 위치를 미리 확인해 두시는 것을 권장드립니다."
                )

        # Safe route info
        if evidence["safe_route_exists_500m"]:
            report_parts.append(
                f"500m 내에 서울시 안심귀갓길이 있어 야간 귀가 시 활용하실 수 있습니다."
            )

        return " ".join(report_parts)
