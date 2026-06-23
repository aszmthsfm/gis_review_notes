# -*- coding: utf-8 -*-
"""导出服务"""

import csv
import json
from typing import List

from ..core.models import ReviewNote
from ..core.enums import STATUS_DISPLAY, PRIORITY_DISPLAY


class ExportService:
    """导出审查意见"""

    def export_to_csv(self, notes: List[ReviewNote], file_path: str) -> bool:
        """导出为 CSV"""
        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "ID", "图层", "要素ID", "审查意见", "优先级",
                    "状态", "作者", "标签", "创建时间", "更新时间"
                ])
                for note in notes:
                    writer.writerow([
                        note.fid,
                        note.layer_name,
                        note.feature_id,
                        note.note_text,
                        PRIORITY_DISPLAY.get(note.priority, "--"),
                        STATUS_DISPLAY.get(note.status, "--"),
                        note.author,
                        note.tags,
                        note.created_at.strftime("%Y-%m-%d %H:%M") if note.created_at else "",
                        note.updated_at.strftime("%Y-%m-%d %H:%M") if note.updated_at else "",
                    ])
            return True
        except Exception as e:
            print(f"导出 CSV 失败: {e}")
            return False

    def export_to_geojson(self, notes: List[ReviewNote], file_path: str) -> bool:
        """导出为 GeoJSON"""
        try:
            features = []
            for note in notes:
                geom = None
                if note.geometry_wkt:
                    # 简单解析 POINT(x y)
                    wkt = note.geometry_wkt
                    if wkt.startswith("POINT("):
                        coords = wkt[6:-1].strip().split()
                        if len(coords) >= 2:
                            geom = {
                                "type": "Point",
                                "coordinates": [float(coords[0]), float(coords[1])]
                            }

                features.append({
                    "type": "Feature",
                    "geometry": geom,
                    "properties": {
                        "fid": note.fid,
                        "layer_name": note.layer_name,
                        "feature_id": note.feature_id,
                        "note_text": note.note_text,
                        "priority": PRIORITY_DISPLAY.get(note.priority, "--"),
                        "status": STATUS_DISPLAY.get(note.status, "--"),
                        "author": note.author,
                        "tags": note.tags,
                        "created_at": note.created_at.isoformat() if note.created_at else None,
                        "updated_at": note.updated_at.isoformat() if note.updated_at else None,
                    }
                })

            geojson = {"type": "FeatureCollection", "features": features}
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(geojson, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"导出 GeoJSON 失败: {e}")
            return False
