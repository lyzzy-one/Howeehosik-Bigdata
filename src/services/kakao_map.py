"""Kakao Map API service."""
import httpx
from typing import Optional, List, Dict, Any

from src.config import get_settings


class KakaoMapService:
    """Kakao Map API wrapper for various map operations."""

    BASE_URL = "https://dapi.kakao.com/v2/local"

    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.kakao_rest_api_key

    def _get_headers(self) -> dict:
        """Get authorization headers."""
        return {
            "Authorization": f"KakaoAK {self.api_key}"
        }

    async def address_to_coords(
        self,
        address: str
    ) -> Optional[Dict[str, Any]]:
        """
        Convert address to coordinates.

        Args:
            address: Korean address string

        Returns:
            Dict with lat, lng, address_name or None
        """
        url = f"{self.BASE_URL}/search/address.json"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self._get_headers(),
                params={"query": address}
            )

            if response.status_code != 200:
                return None

            data = response.json()

            if not data.get("documents"):
                return None

            doc = data["documents"][0]

            return {
                "lat": float(doc["y"]),
                "lng": float(doc["x"]),
                "address_name": doc.get("address_name", address)
            }

    async def coords_to_address(
        self,
        lat: float,
        lng: float
    ) -> Optional[str]:
        """
        Convert coordinates to address (reverse geocoding).

        Args:
            lat: Latitude
            lng: Longitude

        Returns:
            Address string or None
        """
        url = f"{self.BASE_URL}/geo/coord2address.json"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self._get_headers(),
                params={
                    "x": lng,
                    "y": lat
                }
            )

            if response.status_code != 200:
                return None

            data = response.json()

            if not data.get("documents"):
                return None

            doc = data["documents"][0]

            # Prefer road address if available
            if doc.get("road_address"):
                return doc["road_address"]["address_name"]

            return doc.get("address", {}).get("address_name")

    async def search_keyword(
        self,
        keyword: str,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        radius: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Search places by keyword.

        Args:
            keyword: Search keyword
            lat: Center latitude (optional)
            lng: Center longitude (optional)
            radius: Search radius in meters (default: 1000)

        Returns:
            List of place results
        """
        url = f"{self.BASE_URL}/search/keyword.json"

        params = {
            "query": keyword,
            "size": 15
        }

        if lat and lng:
            params["x"] = lng
            params["y"] = lat
            params["radius"] = radius
            params["sort"] = "distance"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self._get_headers(),
                params=params
            )

            if response.status_code != 200:
                return []

            data = response.json()

            return [
                {
                    "name": doc["place_name"],
                    "address": doc["address_name"],
                    "lat": float(doc["y"]),
                    "lng": float(doc["x"]),
                    "distance": doc.get("distance"),
                    "category": doc.get("category_name")
                }
                for doc in data.get("documents", [])
            ]
