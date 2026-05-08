"""Application configuration settings."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Keys
    kakao_rest_api_key: str = ""
    anthropic_api_key: str = ""

    # App Settings
    app_env: str = "development"
    debug: bool = True

    # Data Paths
    data_raw_path: str = "data/raw"
    data_processed_path: str = "data/processed"

    # Scoring Weights (인프라 중시)
    weight_surveillance: float = 0.30  # 감시 인프라 30%
    weight_lighting: float = 0.30      # 야간 조명 30%
    weight_emergency: float = 0.20     # 긴급 대응 20%
    weight_safe_policy: float = 0.10   # 안심정책 10%
    weight_route_access: float = 0.10  # 귀가 접근성 10%

    # Radius Settings (meters)
    radius_near: int = 50
    radius_close: int = 100
    radius_medium: int = 300
    radius_far: int = 500

    # Seoul Bounding Box (for address validation)
    seoul_lat_min: float = 37.413294
    seoul_lat_max: float = 37.715133
    seoul_lng_min: float = 126.734086
    seoul_lng_max: float = 127.269311

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
