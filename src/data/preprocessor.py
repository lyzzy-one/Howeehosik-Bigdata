"""Data preprocessing utilities."""
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString
from typing import Optional, List, Tuple
import re

from src.data.loader import DataLoader
from src.config import get_settings


class DataPreprocessor:
    """Preprocess raw data files into GeoDataFrames."""

    # Seoul bounding box
    SEOUL_BOUNDS = {
        "lat_min": 37.413294,
        "lat_max": 37.715133,
        "lng_min": 126.734086,
        "lng_max": 127.269311
    }

    def __init__(self):
        self.loader = DataLoader()
        self.settings = get_settings()

    def preprocess_cctv(
        self,
        input_file: str = "cctv_seoul.csv",
        output_file: str = "cctv.geojson"
    ) -> gpd.GeoDataFrame:
        """
        Preprocess CCTV data.

        Expected columns: 위도, 경도 (or similar variants)
        """
        df = self.loader.load_csv(input_file)

        # Find lat/lng columns
        lat_col, lng_col = self._find_coord_columns(df)

        # Clean and filter
        df = self._clean_coordinates(df, lat_col, lng_col)
        df = self._filter_seoul(df, lat_col, lng_col)

        # Create GeoDataFrame
        gdf = self._create_geodataframe(df, lat_col, lng_col)

        # Save
        self.loader.save_geojson(gdf, output_file)

        return gdf

    def preprocess_streetlight(
        self,
        input_file: str = "streetlight.csv",
        output_file: str = "streetlight.geojson"
    ) -> gpd.GeoDataFrame:
        """Preprocess streetlight data."""
        df = self.loader.load_csv(input_file)
        lat_col, lng_col = self._find_coord_columns(df)
        df = self._clean_coordinates(df, lat_col, lng_col)
        df = self._filter_seoul(df, lat_col, lng_col)
        gdf = self._create_geodataframe(df, lat_col, lng_col)
        self.loader.save_geojson(gdf, output_file)
        return gdf

    def preprocess_walklight(
        self,
        input_file: str = "walklight.csv",
        output_file: str = "walklight.geojson"
    ) -> gpd.GeoDataFrame:
        """Preprocess pedestrian light data."""
        df = self.loader.load_csv(input_file)
        lat_col, lng_col = self._find_coord_columns(df)
        df = self._clean_coordinates(df, lat_col, lng_col)
        df = self._filter_seoul(df, lat_col, lng_col)
        gdf = self._create_geodataframe(df, lat_col, lng_col)
        self.loader.save_geojson(gdf, output_file)
        return gdf

    def preprocess_emergency_bell(
        self,
        input_file: str = "emergency_bell.csv",
        output_file: str = "emergency_bell.geojson"
    ) -> gpd.GeoDataFrame:
        """Preprocess emergency bell data."""
        df = self.loader.load_csv(input_file)
        lat_col, lng_col = self._find_coord_columns(df)
        df = self._clean_coordinates(df, lat_col, lng_col)
        df = self._filter_seoul(df, lat_col, lng_col)
        gdf = self._create_geodataframe(df, lat_col, lng_col)
        self.loader.save_geojson(gdf, output_file)
        return gdf

    def preprocess_safe_facility(
        self,
        input_file: str = "safe_facility.csv",
        output_file: str = "safe_facility.geojson"
    ) -> gpd.GeoDataFrame:
        """Preprocess safe facility data."""
        df = self.loader.load_csv(input_file)
        lat_col, lng_col = self._find_coord_columns(df)
        df = self._clean_coordinates(df, lat_col, lng_col)
        df = self._filter_seoul(df, lat_col, lng_col)
        gdf = self._create_geodataframe(df, lat_col, lng_col)
        self.loader.save_geojson(gdf, output_file)
        return gdf

    def preprocess_safe_route(
        self,
        input_file: str = "safe_route.csv",
        output_file: str = "safe_route.geojson"
    ) -> gpd.GeoDataFrame:
        """
        Preprocess safe route data.

        Safe routes may have LineString geometry or coordinate pairs.
        """
        df = self.loader.load_csv(input_file)

        # Check if geometry column exists
        if "geometry" in df.columns or "GEOMETRY" in df.columns:
            geom_col = "geometry" if "geometry" in df.columns else "GEOMETRY"
            gdf = gpd.GeoDataFrame(
                df,
                geometry=gpd.GeoSeries.from_wkt(df[geom_col]),
                crs="EPSG:4326"
            )
        else:
            # Try to find coordinate columns and create points
            lat_col, lng_col = self._find_coord_columns(df)
            df = self._clean_coordinates(df, lat_col, lng_col)
            df = self._filter_seoul(df, lat_col, lng_col)
            gdf = self._create_geodataframe(df, lat_col, lng_col)

        self.loader.save_geojson(gdf, output_file)
        return gdf

    def preprocess_all(self) -> dict:
        """Preprocess all data files."""
        results = {}

        # List of preprocessing methods and their files
        preprocessors = [
            ("cctv", self.preprocess_cctv),
            ("streetlight", self.preprocess_streetlight),
            ("walklight", self.preprocess_walklight),
            ("emergency_bell", self.preprocess_emergency_bell),
            ("safe_facility", self.preprocess_safe_facility),
            ("safe_route", self.preprocess_safe_route),
        ]

        for name, func in preprocessors:
            try:
                gdf = func()
                results[name] = {
                    "status": "success",
                    "count": len(gdf)
                }
            except FileNotFoundError as e:
                results[name] = {
                    "status": "skipped",
                    "error": str(e)
                }
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "error": str(e)
                }

        return results

    def _find_coord_columns(
        self,
        df: pd.DataFrame
    ) -> Tuple[str, str]:
        """Find latitude and longitude columns."""
        lat_patterns = ["위도", "lat", "latitude", "y", "Y", "LAT"]
        lng_patterns = ["경도", "lng", "lon", "longitude", "x", "X", "LON", "LNG"]

        lat_col = None
        lng_col = None

        for col in df.columns:
            col_lower = col.lower()
            if any(p.lower() in col_lower for p in lat_patterns):
                lat_col = col
            if any(p.lower() in col_lower for p in lng_patterns):
                lng_col = col

        if not lat_col or not lng_col:
            raise ValueError(
                f"Could not find coordinate columns. "
                f"Available columns: {df.columns.tolist()}"
            )

        return lat_col, lng_col

    def _clean_coordinates(
        self,
        df: pd.DataFrame,
        lat_col: str,
        lng_col: str
    ) -> pd.DataFrame:
        """Clean coordinate data."""
        # Convert to numeric
        df = df.copy()
        df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
        df[lng_col] = pd.to_numeric(df[lng_col], errors="coerce")

        # Drop rows with null coordinates
        df = df.dropna(subset=[lat_col, lng_col])

        # Drop rows with obviously invalid coordinates
        df = df[
            (df[lat_col] > 33) & (df[lat_col] < 39) &
            (df[lng_col] > 124) & (df[lng_col] < 132)
        ]

        return df

    def _filter_seoul(
        self,
        df: pd.DataFrame,
        lat_col: str,
        lng_col: str
    ) -> pd.DataFrame:
        """Filter data to Seoul bounds."""
        return df[
            (df[lat_col] >= self.SEOUL_BOUNDS["lat_min"]) &
            (df[lat_col] <= self.SEOUL_BOUNDS["lat_max"]) &
            (df[lng_col] >= self.SEOUL_BOUNDS["lng_min"]) &
            (df[lng_col] <= self.SEOUL_BOUNDS["lng_max"])
        ]

    def _create_geodataframe(
        self,
        df: pd.DataFrame,
        lat_col: str,
        lng_col: str
    ) -> gpd.GeoDataFrame:
        """Create GeoDataFrame from DataFrame with coordinates."""
        geometry = [
            Point(lng, lat)
            for lat, lng in zip(df[lat_col], df[lng_col])
        ]

        gdf = gpd.GeoDataFrame(
            df,
            geometry=geometry,
            crs="EPSG:4326"
        )

        # Standardize coordinate column names
        gdf = gdf.rename(columns={
            lat_col: "lat",
            lng_col: "lng"
        })

        return gdf
