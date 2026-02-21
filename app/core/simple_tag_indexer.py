from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import pandas as pd


@dataclass
class SimpleTagRecord:
    """Representation of a single row in the simple tag CSV."""

    idx: int
    jst_time: str
    gps_time: Optional[str]
    tag: str
    lat: Optional[float]
    lon: Optional[float]
    alt: Optional[float]
    raw: dict


class SimpleTagIndexer:
    """
    Load and search simple tag CSV files. Provides a search method returning
    SimpleTagRecord objects.
    """

    def __init__(self) -> None:
        self.df: Optional[pd.DataFrame] = None

    def load_csv(self, csv_path: str) -> None:
        """Load a CSV file containing simple tags into a DataFrame."""
        path = Path(csv_path)
        try:
            df = pd.read_csv(path, encoding="utf-8")
        except UnicodeDecodeError:
            # Fallback to cp932 (Shift-JIS) if UTF-8 fails
            df = pd.read_csv(path, encoding="cp932")
        self.df = df

    def search(self, keyword: str, limit: int = 200) -> List[SimpleTagRecord]:
        """Search the loaded DataFrame by a keyword on the 'tag' column."""
        if self.df is None or not keyword:
            return []
        df = self.df
        # Ensure 'tag' column exists
        if 'tag' not in df.columns:
            return []
        mask = df['tag'].astype(str).str.contains(keyword, case=False, na=False)
        hits = df[mask].head(limit)
        results: List[SimpleTagRecord] = []
        for idx, row in hits.iterrows():
            results.append(
                SimpleTagRecord(
                    idx=int(idx),
                    jst_time=str(row.get('timestamp', '')),
                    gps_time=row.get('gps_time'),
                    tag=str(row.get('tag', '')),
                    lat=_to_float(row.get('lat')),
                    lon=_to_float(row.get('lon')),
                    alt=_to_float(row.get('alt')),
                    raw=row.to_dict(),
                )
            )
        return results


def _to_float(value) -> Optional[float]:
    """Utility to convert a value to float, returning None on failure or NaN."""
    try:
        if value is None:
            return None
        # pandas NaN isn't equal to itself
        if value != value:
            return None
        return float(value)
    except Exception:
        return None