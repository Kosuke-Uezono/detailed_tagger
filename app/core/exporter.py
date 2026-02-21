from __future__ import annotations

from pathlib import Path
import pandas as pd
from .annotation_store import AnnotationStore


class Exporter:
    """
    Exporter writes annotation records to a normalized CSV file. It merges
    simple tag information if present.
    """

    def export_csv(self, store: AnnotationStore, output_path: str) -> None:
        rows = []
        for record in store.list_all():
            rows.append(
                {
                    "annotation_id": record.annotation_id,
                    "parent_folder": record.parent_folder,
                    "child_folder": record.child_folder,
                    "media_file": record.media_file,
                    "frame_no": record.frame_no,
                    "lv1": record.lv1,
                    "lv2": record.lv2,
                    "lv3": record.lv3,
                    "created_at": record.created_at,
                    "jst_time": record.jst_time,
                    "gps_time": record.gps_time,
                    "lat": record.lat,
                    "lon": record.lon,
                    "alt": record.alt,
                    "simple_tag": record.simple_tag,
                }
            )
        df = pd.DataFrame(rows)
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_path, index=False, encoding="utf-8-sig")