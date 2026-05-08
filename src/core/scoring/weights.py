"""Scoring weights and thresholds configuration."""

# Category weights (인프라 중시)
CATEGORY_WEIGHTS = {
    "surveillance": 0.30,    # 감시 인프라 30%
    "lighting": 0.30,        # 야간 조명 30%
    "emergency": 0.20,       # 긴급 대응 20%
    "safe_policy": 0.10,     # 안심정책 접근성 10%
    "route_access": 0.10     # 귀가 접근성 10%
}

# Feature weights within categories
FEATURE_WEIGHTS = {
    "surveillance": {
        "cctv_100m_count": 0.3,
        "cctv_300m_count": 0.4,
        "nearest_cctv_distance": 0.3
    },
    "lighting": {
        "streetlight_50m_count": 0.4,
        "streetlight_100m_count": 0.3,
        "walklight_100m_count": 0.3
    },
    "emergency": {
        "emergencybell_300m_count": 0.5,
        "nearest_emergencybell_distance": 0.5
    },
    "safe_policy": {
        "safe_facility_300m_count": 1.0
    },
    "route_access": {
        "nearest_safe_route_distance": 0.6,
        "safe_route_exists_500m": 0.4
    }
}

# Normalization thresholds (count-based: max count for 100 score)
COUNT_THRESHOLDS = {
    "cctv_100m_count": 5,           # 5개 이상 → 100점
    "cctv_300m_count": 15,          # 15개 이상 → 100점
    "streetlight_50m_count": 3,     # 3개 이상 → 100점
    "streetlight_100m_count": 8,    # 8개 이상 → 100점
    "walklight_100m_count": 5,      # 5개 이상 → 100점
    "emergencybell_300m_count": 3,  # 3개 이상 → 100점
    "safe_facility_300m_count": 3   # 3개 이상 → 100점
}

# Distance thresholds (distance-based: min/max distance for 100/0 score)
DISTANCE_THRESHOLDS = {
    "nearest_cctv_distance": {
        "min": 50,    # 50m 이하 → 100점
        "max": 300    # 300m 이상 → 0점
    },
    "nearest_emergencybell_distance": {
        "min": 100,   # 100m 이하 → 100점
        "max": 500    # 500m 이상 → 0점
    },
    "nearest_safe_route_distance": {
        "min": 100,   # 100m 이하 → 100점
        "max": 500    # 500m 이상 → 0점
    }
}

# Grade thresholds
GRADE_THRESHOLDS = [
    (85, "매우 양호"),
    (70, "양호"),
    (55, "보통"),
    (40, "미흡"),
    (0, "취약")
]


def get_grade(score: float) -> str:
    """Get grade string for given score."""
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "취약"
