"""Data loading utilities."""
import pandas as pd
import geopandas as gpd
from pathlib import Path
from typing import Optional

from src.config import get_settings


class DataLoader:
    """Load raw and processed data files."""

    def __init__(self):
        self.settings = get_settings()
        self.raw_path = Path(self.settings.data_raw_path)
        self.processed_path = Path(self.settings.data_processed_path)

    def load_csv(self, filename: str, encoding: str = "utf-8") -> pd.DataFrame:
        """
        Load CSV file from raw data directory.

        Args:
            filename: Name of the CSV file
            encoding: File encoding (default: utf-8)

        Returns:
            DataFrame with loaded data
        """
        filepath = self.raw_path / filename

        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        # Try multiple encodings
        encodings = [encoding, "cp949", "euc-kr", "utf-8-sig"]

        for enc in encodings:
            try:
                return pd.read_csv(filepath, encoding=enc)
            except UnicodeDecodeError:
                continue

        raise ValueError(f"Could not decode file with any encoding: {filepath}")

    def load_geojson(self, filename: str) -> gpd.GeoDataFrame:
        """
        Load GeoJSON file from processed data directory.

        Args:
            filename: Name of the GeoJSON file

        Returns:
            GeoDataFrame with loaded data
        """
        filepath = self.processed_path / filename

        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        return gpd.read_file(filepath)

    def save_geojson(
        self,
        gdf: gpd.GeoDataFrame,
        filename: str
    ) -> Path:
        """
        Save GeoDataFrame as GeoJSON.

        Args:
            gdf: GeoDataFrame to save
            filename: Output filename

        Returns:
            Path to saved file
        """
        self.processed_path.mkdir(parents=True, exist_ok=True)
        filepath = self.processed_path / filename

        gdf.to_file(filepath, driver="GeoJSON")

        return filepath

    def list_raw_files(self) -> list:
        """List all files in raw data directory."""
        if not self.raw_path.exists():
            return []
        return list(self.raw_path.glob("*"))

    def list_processed_files(self) -> list:
        """List all files in processed data directory."""
        if not self.processed_path.exists():
            return []
        return list(self.processed_path.glob("*"))
