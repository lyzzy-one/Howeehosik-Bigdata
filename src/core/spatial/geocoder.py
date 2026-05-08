"""Kakao Map Geocoding module."""
import httpx
from typing import Optional

from src.config import get_settings


class KakaoGeocoder:
    """Kakao Map API based geocoder."""

    BASE_URL = "https://dapi.kakao.com/v2/local/search/address.json"

    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.kakao_rest_api_key

    async def geocode(self, address: str) -> Optional[dict]:
        """
        Convert address to coordinates.

        Args:
            address: Korean address string

        Returns:
            dict with lat, lng or None if not found
        """
        if not self.api_key:
            raise ValueError("Kakao API key is not configured")

        headers = {
            "Authorization": f"KakaoAK {self.api_key}"
        }

        params = {
            "query": address
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.BASE_URL,
                headers=headers,
                params=params
            )

            if response.status_code != 200:
                return None

            data = response.json()

            if not data.get("documents"):
                # Try keyword search as fallback
                return await self._keyword_search(address)

            doc = data["documents"][0]

            return {
                "lat": float(doc["y"]),
                "lng": float(doc["x"]),
                "address": doc.get("address_name", address)
            }

    async def _keyword_search(self, keyword: str) -> Optional[dict]:
        """Fallback keyword search."""
        url = "https://dapi.kakao.com/v2/local/search/keyword.json"

        headers = {
            "Authorization": f"KakaoAK {self.api_key}"
        }

        params = {
            "query": keyword
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)

            if response.status_code != 200:
                return None

            data = response.json()

            if not data.get("documents"):
                return None

            doc = data["documents"][0]

            return {
                "lat": float(doc["y"]),
                "lng": float(doc["x"]),
                "address": doc.get("address_name", keyword)
            }

    def is_in_seoul(self, lat: float, lng: float) -> bool:
        """
        Check if coordinates are within Seoul boundaries.

        Args:
            lat: Latitude
            lng: Longitude

        Returns:
            True if within Seoul, False otherwise
        """
        return (
            self.settings.seoul_lat_min <= lat <= self.settings.seoul_lat_max and
            self.settings.seoul_lng_min <= lng <= self.settings.seoul_lng_max
        )
