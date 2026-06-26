# -*- coding: utf-8 -*-
"""导出服务"""

import csv
import json
from typing import List

# 修改点 1：引入 QgsGeometry 用于健壮的 WKT 解析
from qgis.core import QgsGeometry

from ..core.models import ReviewNote
from ..core.enums import STATUS_DISPLAY, PRIORITY_DISPLAY
# 修改点 2：引入标准日志工具
from ..utils.logger import log_error


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
            # 修改点 3：使用标准错误日志记录
            log_error(f"导出 CSV 失败: {e}")
            return False

    def export_to_geojson(self, notes: List[ReviewNote], file_path: str) -> bool:
        """导出为 GeoJSON"""
        try:
            features = []
            for note in notes:
                geom = None
                if note.geometry_wkt:
                    # 修改点 4：使用 QgsGeometry 替代脆弱的字符串切片
                    qgs_geom = QgsGeometry.fromWkt(note.geometry_wkt)
                    if not qgs_geom.isEmpty():
                        # asJson() 返回的已经是 json 格式的字符串，需转为字典以嵌入 GeoJSON
                        geom = json.loads(qgs_geom.asJson())

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
            # 修改点 5：使用标准错误日志记录
            log_error(f"导出 GeoJSON 失败: {e}")
            return False