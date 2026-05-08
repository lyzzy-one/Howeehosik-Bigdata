"""Score normalization functions."""
from typing import Optional

from src.core.scoring.weights import COUNT_THRESHOLDS, DISTANCE_THRESHOLDS


class ScoreNormalizer:
    """Normalize raw values to 0-100 scores."""

    @staticmethod
    def normalize_count(value: int, feature_name: str) -> float:
        """
        Normalize count-based feature to 0-100 score.

        Higher count = higher score (capped at threshold).

        Args:
            value: Raw count value
            feature_name: Name of feature for threshold lookup

        Returns:
            Normalized score (0-100)
        """
        threshold = COUNT_THRESHOLDS.get(feature_name, 10)

        if value >= threshold:
            return 100.0

        return (value / threshold) * 100

    @staticmethod
    def normalize_distance(
        value: Optional[float],
        feature_name: str
    ) -> float:
        """
        Normalize distance-based feature to 0-100 score.

        Shorter distance = higher score (inverse relationship).

        Args:
            value: Distance in meters, or None if not found
            feature_name: Name of feature for threshold lookup

        Returns:
            Normalized score (0-100)
        """
        if value is None:
            return 0.0

        thresholds = DISTANCE_THRESHOLDS.get(feature_name, {"min": 100, "max": 500})
        min_dist = thresholds["min"]
        max_dist = thresholds["max"]

        if value <= min_dist:
            return 100.0

        if value >= max_dist:
            return 0.0

        # Linear interpolation
        return ((max_dist - value) / (max_dist - min_dist)) * 100

    @staticmethod
    def normalize_boolean(value: bool) -> float:
        """
        Normalize boolean feature to 0-100 score.

        Args:
            value: Boolean value

        Returns:
            100 if True, 0 if False
        """
        return 100.0 if value else 0.0
