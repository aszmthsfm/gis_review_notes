# -*- coding: utf-8 -*-
"""审查批注核心业务逻辑"""

import os
from typing import Optional, List

from qgis.core import QgsProject, QgsVectorLayer, QgsFeature

from ..core.models import ReviewNote, ProjectBinding
from ..core.enums import ReviewStatus, NotePriority
from ..core.constants import Constants
from ..data.note_repository import NoteRepository
from ..data.project_meta_repository import ProjectMetaRepository
from ..utils.hash_utils import compute_project_hash
from ..utils.geo_utils import feature_to_centroid_wkt
from ..utils.logger import log_info, log_error


class NoteService:
    """审查意见核心业务逻辑层"""

    def __init__(self, note_repo: NoteRepository,
                 project_meta_repo: ProjectMetaRepository):
        self._note_repo = note_repo
        self._project_meta_repo = project_meta_repo
        self._current_project_hash: str = ""

    # ═══════════════════════════════════════
    #  项目哈希
    # ═══════════════════════════════════════

    @property
    def current_project_hash(self) -> str:
        return self._current_project_hash

    def update_project_hash(self) -> str:
        """根据当前 QGIS 项目计算并更新哈希"""
        project = QgsProject.instance()
        path = project.fileName()
        self._current_project_hash = compute_project_hash(path)
        return self._current_project_hash

    def register_project_binding(self, gpkg_path: str) -> None:
        """注册或更新当前项目的绑定关系"""
        project = QgsProject.instance()
        path = project.fileName()
        title = project.title() or os.path.basename(path) if path else "未保存项目"

        binding = ProjectBinding(
            project_hash=self._current_project_hash,
            project_path=path,
            gpkg_path=gpkg_path,
            project_title=title,
        )
        self._project_meta_repo.upsert(binding)
        log_info(f"项目绑定已更新: {title}")

    # ═══════════════════════════════════════
    #  批注 CRUD
    # ═══════════════════════════════════════

    def add_note(self, layer: QgsVectorLayer, feature: QgsFeature,
                 text: str, priority: NotePriority = NotePriority.MEDIUM,
                 author: str = "", tags: str = "") -> ReviewNote:
        """添加一条审查批注"""
        if not self._current_project_hash:
            self.update_project_hash()

        # 获取要素质心 WKT
        geometry_wkt = ""
        try:
            geometry_wkt = feature_to_centroid_wkt(feature, layer.crs())
        except Exception as e:
            log_error(f"获取要素质心失败: {e}")

        note = ReviewNote(
            project_hash=self._current_project_hash,
            layer_id=layer.id(),
            layer_name=layer.name(),
            feature_id=feature.id(),
            note_text=text,
            status=ReviewStatus.OPEN,
            priority=priority,
            author=author,
            tags=tags,
            geometry_wkt=geometry_wkt,
        )

        fid = self._note_repo.insert(note)
        note.fid = fid

        # ----记录创建历史 ----
        self._note_repo.insert_history(fid, "新建", "创建了批注", author)

        log_info(f"新增批注 #{fid}: {layer.name()} F:{feature.id()}")
        return note

    def update_note(self, fid: int, note_text: str = None,
                    priority: NotePriority = None, tags: str = None,
                    author: str = None) -> Optional[ReviewNote]:
        """更新批注内容"""
        note = self._note_repo.get_by_id(fid)
        if not note:
            return None

        # ---- 新增：对比变更内容 ----
        changes = []
        if note_text is not None and note_text != note.note_text:
            changes.append("内容")
        if priority is not None and priority != note.priority:
            changes.append("优先级")
        if tags is not None and tags != note.tags:
            changes.append("标签")

        if note_text is not None:
            note.note_text = note_text
        if priority is not None:
            note.priority = priority
        if tags is not None:
            note.tags = tags
        if author is not None:
            note.author = author

        self._note_repo.update(note)

        # ---- 写入历史 ----
        if changes:
            detail = "修改了: " + ", ".join(changes)
            self._note_repo.insert_history(fid, "编辑", detail, author or note.author)

        return note

    def delete_note(self, fid: int) -> bool:
        return self._note_repo.delete(fid)

    def change_status(self, fid: int, status: ReviewStatus) -> bool:
        # 获取原状态以作对比
        note = self.get_note_by_id(fid)

        success = self._note_repo.update_status(fid, status)

        # 写入状态变更历史
        if success and note and note.status != status:
            from ..core.enums import STATUS_DISPLAY
            old_str = STATUS_DISPLAY.get(note.status, str(note.status))
            new_str = STATUS_DISPLAY.get(status, str(status))
            self._note_repo.insert_history(
                fid, "状态变更", f"由 [{old_str}] 变更为 [{new_str}]", note.author
            )

        return success

    def get_note_by_id(self, fid: int) -> Optional[ReviewNote]:
        return self._note_repo.get_by_id(fid)

    # ═══════════════════════════════════════
    #  查询
    # ═══════════════════════════════════════

    def get_notes_for_current_project(self) -> List[ReviewNote]:
        if not self._current_project_hash:
            self.update_project_hash()
        return self._note_repo.get_by_project(self._current_project_hash)

    def get_notes_for_layer(self, layer_id: str) -> List[ReviewNote]:
        if not self._current_project_hash:
            self.update_project_hash()
        return self._note_repo.get_by_layer(self._current_project_hash, layer_id)

    def get_notes_for_feature(self, layer_id: str, feature_id: int) -> List[ReviewNote]:
        if not self._current_project_hash:
            self.update_project_hash()
        return self._note_repo.get_by_feature(self._current_project_hash, layer_id, feature_id)

    def search(self, status: str = "all", priorities: list = None,
               layer_name: str = "") -> List[ReviewNote]:
        if not self._current_project_hash:
            self.update_project_hash()
        return self._note_repo.search(
            self._current_project_hash, status, priorities, layer_name
        )

    def get_statistics(self) -> dict:
        if not self._current_project_hash:
            self.update_project_hash()
        counts = self._note_repo.count_by_status(self._current_project_hash)
        return {
            "pending": counts.get("open", 0),
            "in_progress": counts.get("in_progress", 0),
            "resolved": counts.get("resolved", 0),
            "wontfix": counts.get("wontfix", 0),
            "total": sum(counts.values()),
        }

    def get_layer_names_for_project(self) -> list:
        if not self._current_project_hash:
            self.update_project_hash()
        return self._note_repo.get_layer_names(self._current_project_hash)

    def get_note_history(self, fid: int) -> list:
        return self._note_repo.get_history(fid)
