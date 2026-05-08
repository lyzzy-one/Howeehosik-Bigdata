"""Safety score calculation engine."""
from typing import Dict, Any

from src.core.spatial.analyzer import SpatialAnalyzer
from src.core.scoring.normalizer import ScoreNormalizer
from src.core.scoring.weights import (
    CATEGORY_WEIGHTS,
    FEATURE_WEIGHTS,
    get_grade
)
from src.services.claude_ai import ClaudeReportGenerator
from src.models.response import (
    SafetyScoreResponse,
    SafetyScoreData,
    Coordinates,
    CategoryScore,
    CategoryScores,
    Evidence
)
from src.config import get_settings


class SafetyScoreCalculator:
    """Calculate safety scores for a location."""

    def __init__(self):
        self.settings = get_settings()
        self.analyzer = SpatialAnalyzer()
        self.normalizer = ScoreNormalizer()
        self.report_generator = ClaudeReportGenerator()

    async def calculate(
        self,
        lat: float,
        lng: float,
        address: str
    ) -> SafetyScoreResponse:
        """
        Calculate safety score for given coordinates.

        Args:
            lat: Latitude
            lng: Longitude
            address: Original address string

        Returns:
            SafetyScoreResponse with all calculated scores
        """
        # 1. Extract features
        evidence = self._extract_features(lat, lng)

        # 2. Calculate category scores
        category_scores = self._calculate_category_scores(evidence)

        # 3. Calculate total score
        total_score = self._calculate_total_score(category_scores)
        grade = get_grade(total_score)

        # 4. Generate AI report
        ai_report = await self.report_generator.generate_report(
            address=address,
            total_score=total_score,
            grade=grade,
            category_scores=category_scores,
            evidence=evidence
        )

        # 5. Build response
        return SafetyScoreResponse(
            success=True,
            data=SafetyScoreData(
                address=address,
                coordinates=Coordinates(lat=lat, lng=lng),
                total_score=total_score,
                grade=grade,
                category_scores=CategoryScores(
                    surveillance=category_scores["surveillance"],
                    lighting=category_scores["lighting"],
                    emergency=category_scores["emergency"],
                    safe_policy=category_scores["safe_policy"],
                    route_access=category_scores["route_access"]
                ),
                evidence=Evidence(**evidence),
                ai_report=ai_report
            )
        )

    def _extract_features(self, lat: float, lng: float) -> Dict[str, Any]:
        """Extract all features for scoring."""
        # Load data
        cctv_data = self.analyzer.load_data("cctv")
        streetlight_data = self.analyzer.load_data("streetlight")
        walklight_data = self.analyzer.load_data("walklight")
        emergency_bell_data = self.analyzer.load_data("emergency_bell")
        safe_facility_data = self.analyzer.load_data("safe_facility")
        safe_route_data = self.analyzer.load_data("safe_route")

        # CCTV features
        cctv_100m_count = self.analyzer.count_within_radius(
            lat, lng, cctv_data, 100
        )
        cctv_300m_count = self.analyzer.count_within_radius(
            lat, lng, cctv_data, 300
        )
        nearest_cctv_distance = self.analyzer.get_nearest_distance(
            lat, lng, cctv_data, 500
        )

        # Streetlight features
        streetlight_50m_count = self.analyzer.count_within_radius(
            lat, lng, streetlight_data, 50
        )
        streetlight_100m_count = self.analyzer.count_within_radius(
            lat, lng, streetlight_data, 100
        )

        # Walklight features
        walklight_100m_count = self.analyzer.count_within_radius(
            lat, lng, walklight_data, 100
        )

        # Emergency bell features
        emergencybell_300m_count = self.analyzer.count_within_radius(
            lat, lng, emergency_bell_data, 300
        )
        nearest_emergencybell_distance = self.analyzer.get_nearest_distance(
            lat, lng, emergency_bell_data, 500
        )

        # Safe facility features
        safe_facility_300m_count = self.analyzer.count_within_radius(
            lat, lng, safe_facility_data, 300
        )

        # Safe route features
        nearest_safe_route_distance = self.analyzer.get_nearest_line_distance(
            lat, lng, safe_route_data, 500
        )
        safe_route_exists_500m = self.analyzer.check_route_exists_within_radius(
            lat, lng, safe_route_data, 500
        )

        return {
            "cctv_100m_count": cctv_100m_count,
            "cctv_300m_count": cctv_300m_count,
            "nearest_cctv_distance_m": nearest_cctv_distance,
            "streetlight_50m_count": streetlight_50m_count,
            "streetlight_100m_count": streetlight_100m_count,
            "walklight_100m_count": walklight_100m_count,
            "emergencybell_300m_count": emergencybell_300m_count,
            "nearest_emergencybell_distance_m": nearest_emergencybell_distance,
            "safe_facility_300m_count": safe_facility_300m_count,
            "nearest_safe_route_distance_m": nearest_safe_route_distance,
            "safe_route_exists_500m": safe_route_exists_500m
        }

    def _calculate_category_scores(
        self,
        evidence: Dict[str, Any]
    ) -> Dict[str, CategoryScore]:
        """Calculate scores for each category."""
        scores = {}

        # Surveillance (30%)
        surveillance_features = {
            "cctv_100m_count": self.normalizer.normalize_count(
                evidence["cctv_100m_count"], "cctv_100m_count"
            ),
            "cctv_300m_count": self.normalizer.normalize_count(
                evidence["cctv_300m_count"], "cctv_300m_count"
            ),
            "nearest_cctv_distance": self.normalizer.normalize_distance(
                evidence["nearest_cctv_distance_m"], "nearest_cctv_distance"
            )
        }
        surveillance_percentage = self._weighted_average(
            surveillance_features,
            FEATURE_WEIGHTS["surveillance"]
        )
        max_surveillance = CATEGORY_WEIGHTS["surveillance"] * 100
        scores["surveillance"] = CategoryScore(
            score=round(surveillance_percentage * CATEGORY_WEIGHTS["surveillance"], 1),
            max=max_surveillance,
            percentage=int(surveillance_percentage)
        )

        # Lighting (30%)
        lighting_features = {
            "streetlight_50m_count": self.normalizer.normalize_count(
                evidence["streetlight_50m_count"], "streetlight_50m_count"
            ),
            "streetlight_100m_count": self.normalizer.normalize_count(
                evidence["streetlight_100m_count"], "streetlight_100m_count"
            ),
            "walklight_100m_count": self.normalizer.normalize_count(
                evidence["walklight_100m_count"], "walklight_100m_count"
            )
        }
        lighting_percentage = self._weighted_average(
            lighting_features,
            FEATURE_WEIGHTS["lighting"]
        )
        max_lighting = CATEGORY_WEIGHTS["lighting"] * 100
        scores["lighting"] = CategoryScore(
            score=round(lighting_percentage * CATEGORY_WEIGHTS["lighting"], 1),
            max=max_lighting,
            percentage=int(lighting_percentage)
        )

        # Emergency (20%)
        emergency_features = {
            "emergencybell_300m_count": self.normalizer.normalize_count(
                evidence["emergencybell_300m_count"], "emergencybell_300m_count"
            ),
            "nearest_emergencybell_distance": self.normalizer.normalize_distance(
                evidence["nearest_emergencybell_distance_m"],
                "nearest_emergencybell_distance"
            )
        }
        emergency_percentage = self._weighted_average(
            emergency_features,
            FEATURE_WEIGHTS["emergency"]
        )
        max_emergency = CATEGORY_WEIGHTS["emergency"] * 100
        scores["emergency"] = CategoryScore(
            score=round(emergency_percentage * CATEGORY_WEIGHTS["emergency"], 1),
            max=max_emergency,
            percentage=int(emergency_percentage)
        )

        # Safe Policy (10%)
        safe_policy_features = {
            "safe_facility_300m_count": self.normalizer.normalize_count(
                evidence["safe_facility_300m_count"], "safe_facility_300m_count"
            )
        }
        safe_policy_percentage = self._weighted_average(
            safe_policy_features,
            FEATURE_WEIGHTS["safe_policy"]
        )
        max_safe_policy = CATEGORY_WEIGHTS["safe_policy"] * 100
        scores["safe_policy"] = CategoryScore(
            score=round(safe_policy_percentage * CATEGORY_WEIGHTS["safe_policy"], 1),
            max=max_safe_policy,
            percentage=int(safe_policy_percentage)
        )

        # Route Access (10%)
        route_access_features = {
            "nearest_safe_route_distance": self.normalizer.normalize_distance(
                evidence["nearest_safe_route_distance_m"],
                "nearest_safe_route_distance"
            ),
            "safe_route_exists_500m": self.normalizer.normalize_boolean(
                evidence["safe_route_exists_500m"]
            )
        }
        route_access_percentage = self._weighted_average(
            route_access_features,
            FEATURE_WEIGHTS["route_access"]
        )
        max_route_access = CATEGORY_WEIGHTS["route_access"] * 100
        scores["route_access"] = CategoryScore(
            score=round(route_access_percentage * CATEGORY_WEIGHTS["route_access"], 1),
            max=max_route_access,
            percentage=int(route_access_percentage)
        )

        return scores

    def _weighted_average(
        self,
        feature_scores: Dict[str, float],
        weights: Dict[str, float]
    ) -> float:
        """Calculate weighted average of feature scores."""
        total = 0.0
        for feature_name, score in feature_scores.items():
            weight = weights.get(feature_name, 0)
            total += score * weight
        return total

    def _calculate_total_score(
        self,
        category_scores: Dict[str, CategoryScore]
    ) -> int:
        """Calculate total score from category scores."""
        total = sum(cs.score for cs in category_scores.values())
        return int(round(total))
