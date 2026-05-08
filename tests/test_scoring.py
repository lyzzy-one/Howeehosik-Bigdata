"""Tests for scoring module."""
import pytest
from src.core.scoring.normalizer import ScoreNormalizer
from src.core.scoring.weights import get_grade, CATEGORY_WEIGHTS


class TestScoreNormalizer:
    """Tests for ScoreNormalizer class."""

    def test_normalize_count_at_threshold(self):
        """Test count normalization at threshold."""
        normalizer = ScoreNormalizer()
        # CCTV 100m threshold is 5
        assert normalizer.normalize_count(5, "cctv_100m_count") == 100.0
        assert normalizer.normalize_count(10, "cctv_100m_count") == 100.0

    def test_normalize_count_below_threshold(self):
        """Test count normalization below threshold."""
        normalizer = ScoreNormalizer()
        # CCTV 100m threshold is 5
        assert normalizer.normalize_count(0, "cctv_100m_count") == 0.0
        assert normalizer.normalize_count(2, "cctv_100m_count") == 40.0
        assert normalizer.normalize_count(3, "cctv_100m_count") == 60.0

    def test_normalize_distance_at_min(self):
        """Test distance normalization at minimum."""
        normalizer = ScoreNormalizer()
        # nearest_cctv_distance: min=50, max=300
        assert normalizer.normalize_distance(50, "nearest_cctv_distance") == 100.0
        assert normalizer.normalize_distance(30, "nearest_cctv_distance") == 100.0

    def test_normalize_distance_at_max(self):
        """Test distance normalization at maximum."""
        normalizer = ScoreNormalizer()
        # nearest_cctv_distance: min=50, max=300
        assert normalizer.normalize_distance(300, "nearest_cctv_distance") == 0.0
        assert normalizer.normalize_distance(400, "nearest_cctv_distance") == 0.0

    def test_normalize_distance_middle(self):
        """Test distance normalization in middle range."""
        normalizer = ScoreNormalizer()
        # nearest_cctv_distance: min=50, max=300
        # At 175m (midpoint), should be 50%
        score = normalizer.normalize_distance(175, "nearest_cctv_distance")
        assert 45 <= score <= 55

    def test_normalize_distance_none(self):
        """Test distance normalization with None value."""
        normalizer = ScoreNormalizer()
        assert normalizer.normalize_distance(None, "nearest_cctv_distance") == 0.0

    def test_normalize_boolean(self):
        """Test boolean normalization."""
        normalizer = ScoreNormalizer()
        assert normalizer.normalize_boolean(True) == 100.0
        assert normalizer.normalize_boolean(False) == 0.0


class TestGrading:
    """Tests for grade function."""

    def test_grade_very_good(self):
        """Test very good grade."""
        assert get_grade(85) == "매우 양호"
        assert get_grade(100) == "매우 양호"

    def test_grade_good(self):
        """Test good grade."""
        assert get_grade(70) == "양호"
        assert get_grade(84) == "양호"

    def test_grade_average(self):
        """Test average grade."""
        assert get_grade(55) == "보통"
        assert get_grade(69) == "보통"

    def test_grade_poor(self):
        """Test poor grade."""
        assert get_grade(40) == "미흡"
        assert get_grade(54) == "미흡"

    def test_grade_vulnerable(self):
        """Test vulnerable grade."""
        assert get_grade(0) == "취약"
        assert get_grade(39) == "취약"


class TestCategoryWeights:
    """Tests for category weights."""

    def test_weights_sum_to_one(self):
        """Test that all weights sum to 1.0."""
        total = sum(CATEGORY_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_infrastructure_focus(self):
        """Test that surveillance and lighting have highest weights."""
        assert CATEGORY_WEIGHTS["surveillance"] == 0.30
        assert CATEGORY_WEIGHTS["lighting"] == 0.30
        assert CATEGORY_WEIGHTS["emergency"] == 0.20
        assert CATEGORY_WEIGHTS["safe_policy"] == 0.10
        assert CATEGORY_WEIGHTS["route_access"] == 0.10
