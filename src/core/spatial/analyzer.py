"""Spatial analysis module for radius-based queries."""
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, LineString
from shapely.ops import nearest_points
from typing import Optional, Union
import numpy as np
from pathlib import Path

from src.config import get_settings


class SpatialAnalyzer:
    """Spatial analyzer for safety infrastructure data."""

    def __init__(self):
        self.settings = get_settings()
        self._data_cache: dict = {}

    def load_data(self, data_type: str) -> gpd.GeoDataFrame:
        """
        Load processed GeoDataFrame for given data type.

        Args:
            data_type: Type of data (cctv, streetlight, walklight,
                      emergency_bell, safe_facility, safe_route)

        Returns:
            GeoDataFrame with geometry column
        """
        if data_type in self._data_cache:
            return self._data_cache[data_type]

        file_path = Path(self.settings.data_processed_path) / f"{data_type}.geojson"

        if not file_path.exists():
            # Return empty GeoDataFrame if file doesn't exist
            return gpd.GeoDataFrame(
                columns=["geometry"],
                crs="EPSG:4326"
            )

        gdf = gpd.read_file(file_path)
        self._data_cache[data_type] = gdf
        return gdf

    def get_points_within_radius(
        self,
        lat: float,
        lng: float,
        gdf: gpd.GeoDataFrame,
        radius_m: float
    ) -> gpd.GeoDataFrame:
        """
        Get all points within radius from center point.

        Args:
            lat: Center latitude
            lng: Center longitude
            gdf: GeoDataFrame to search
            radius_m: Radius in meters

        Returns:
            GeoDataFrame with points within radius
        """
        if gdf.empty:
            return gdf

        # Create center point
        center = Point(lng, lat)

        # Convert to projected CRS for accurate distance calculation (UTM 52N for Korea)
        gdf_proj = gdf.to_crs("EPSG:32652")
        center_proj = gpd.GeoSeries([center], crs="EPSG:4326").to_crs("EPSG:32652").iloc[0]

        # Create buffer and filter
        buffer = center_proj.buffer(radius_m)
        mask = gdf_proj.geometry.within(buffer)

        return gdf[mask]

    def count_within_radius(
        self,
        lat: float,
        lng: float,
        gdf: gpd.GeoDataFrame,
        radius_m: float
    ) -> int:
        """
        Count points within radius.

        Args:
            lat: Center latitude
            lng: Center longitude
            gdf: GeoDataFrame to search
            radius_m: Radius in meters

        Returns:
            Count of points within radius
        """
        filtered = self.get_points_within_radius(lat, lng, gdf, radius_m)
        return len(filtered)

    def get_nearest_distance(
        self,
        lat: float,
        lng: float,
        gdf: gpd.GeoDataFrame,
        max_distance_m: float = 1000
    ) -> Optional[float]:
        """
        Get distance to nearest point in GeoDataFrame.

        Args:
            lat: Center latitude
            lng: Center longitude
            gdf: GeoDataFrame to search
            max_distance_m: Maximum search distance in meters

        Returns:
            Distance in meters, or None if no point found within max_distance
        """
        if gdf.empty:
            return None

        # Create center point
        center = Point(lng, lat)

        # Convert to projected CRS
        gdf_proj = gdf.to_crs("EPSG:32652")
        center_proj = gpd.GeoSeries([center], crs="EPSG:4326").to_crs("EPSG:32652").iloc[0]

        # Calculate distances
        distances = gdf_proj.geometry.distance(center_proj)

        if distances.empty:
            return None

        min_distance = distances.min()

        if min_distance > max_distance_m:
            return None

        return round(min_distance, 1)

    def get_nearest_line_distance(
        self,
        lat: float,
        lng: float,
        gdf: gpd.GeoDataFrame,
        max_distance_m: float = 1000
    ) -> Optional[float]:
        """
        Get distance to nearest LineString in GeoDataFrame.

        Args:
            lat: Center latitude
            lng: Center longitude
            gdf: GeoDataFrame with LineString geometries
            max_distance_m: Maximum search distance

        Returns:
            Distance in meters, or None if no line found within max_distance
        """
        if gdf.empty:
            return None

        # Create center point
        center = Point(lng, lat)

        # Convert to projected CRS
        gdf_proj = gdf.to_crs("EPSG:32652")
        center_proj = gpd.GeoSeries([center], crs="EPSG:4326").to_crs("EPSG:32652").iloc[0]

        # Calculate distances to each line
        distances = gdf_proj.geometry.distance(center_proj)

        if distances.empty:
            return None

        min_distance = distances.min()

        if min_distance > max_distance_m:
            return None

        return round(min_distance, 1)

    def check_route_exists_within_radius(
        self,
        lat: float,
        lng: float,
        gdf: gpd.GeoDataFrame,
        radius_m: float
    ) -> bool:
        """
        Check if any route exists within radius.

        Args:
            lat: Center latitude
            lng: Center longitude
            gdf: GeoDataFrame with LineString geometries
            radius_m: Radius in meters

        Returns:
            True if any route exists within radius
        """
        distance = self.get_nearest_line_distance(lat, lng, gdf, radius_m)
        return distance is not None
