# -*- coding: utf-8 -*-
"""数据模型定义"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .enums import (
    ReviewStatus,
    NotePriority,
    STATUS_VALUE_MAP,
    PRIORITY_VALUE_MAP,
)


@dataclass
class ReviewNote:
    """审查批注数据模型

    对应数据库 review_notes 表的一条记录。
    """

    fid: Optional[int] = None
    project_hash: str = ""
    layer_id: str = ""
    layer_name: str = ""
    feature_id: int = -1
    note_text: str = ""
    status: ReviewStatus = ReviewStatus.OPEN
    priority: NotePriority = NotePriority.MEDIUM
    author: str = ""
    tags: str = ""
    geometry_wkt: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """转换为字典（用于导出等场景）"""
        return {
            "fid": self.fid,
            "project_hash": self.project_hash,
            "layer_id": self.layer_id,
            "source_layer_name": self.layer_name,
            "feature_id": self.feature_id,
            "note_text": self.note_text,
            "status": self.status.value,
            "priority": self.priority.value,
            "author": self.author,
            "tags": self.tags,
            "geometry_wkt": self.geometry_wkt,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @staticmethod
    def from_db_row(row: tuple) -> "ReviewNote":
        """从数据库行构造对象

        :param row: 数据库行，字段顺序为:
            (fid, project_hash, layer_id, source_layer_name, feature_id,
             note_text, status, priority, author, tags,
             geometry, created_at, updated_at)
        :return: ReviewNote 实例
        """
        # ── 日期解析辅助函数 ──
        def parse_dt(val):
            if val is None:
                return None
            if isinstance(val, datetime):
                return val
            # 尝试 ISO 格式
            try:
                return datetime.fromisoformat(str(val))
            except (ValueError, TypeError):
                pass
            # 尝试 SQLite 默认格式
            try:
                return datetime.strptime(str(val), "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                return None

        # ── 解析状态 ──
        status_val = row[6] if row[6] else "open"
        status = STATUS_VALUE_MAP.get(status_val, ReviewStatus.OPEN)
        if isinstance(status, str):
            status = STATUS_VALUE_MAP.get(status, ReviewStatus.OPEN)

        # ── 解析优先级 ──
        priority_val = row[7] if row[7] else 2
        priority = PRIORITY_VALUE_MAP.get(priority_val, NotePriority.MEDIUM)
        if isinstance(priority, int):
            priority = PRIORITY_VALUE_MAP.get(priority, NotePriority.MEDIUM)

        # ── 构造对象 ──
        return ReviewNote(
            fid=row[0],
            project_hash=row[1] or "",
            layer_id=row[2] or "",
            layer_name=row[3] or "",
            feature_id=row[4] if row[4] is not None else -1,
            note_text=row[5] or "",
            status=status,
            priority=priority,
            author=row[8] or "",
            tags=row[9] or "",
            geometry_wkt=str(row[10]) if row[10] else "",
            created_at=parse_dt(row[11]),
            updated_at=parse_dt(row[12]),
        )


@dataclass
class ProjectBinding:
    """项目与 GPKG 的绑定关系

    对应数据库 project_bindings 表的一条记录。
    一个 QGIS 项目绑定到一个 GPKG 文件，
    一个 GPKG 文件可以服务多个项目（通过 project_hash 隔离）。
    """

    fid: Optional[int] = None
    project_hash: str = ""
    project_path: str = ""
    gpkg_path: str = ""
    project_title: str = ""
    created_at: Optional[datetime] = None
    last_opened: Optional[datetime] = None
