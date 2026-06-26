# -*- coding: utf-8 -*-
"""ReviewNote 数据访问对象 (DAO)"""

from datetime import datetime
from typing import Optional, List
from ..core.models import ReviewNote
from ..core.enums import ReviewStatus, NotePriority
from ..core.constants import Constants
from .connection_manager import ConnectionManager
from ..utils.logger import log_info, log_error


class NoteRepository:
    """审查批注的增删改查"""

    def __init__(self, db_manager):
        """传入数据库管理器，而不是直接传连接"""
        self._db_manager = db_manager

    @property
    def _conn(self):
        """动态获取最新连接，防止拿到旧的 None"""
        return self._db_manager.get_connection()

    def insert(self, note: ReviewNote) -> int:
        """插入一条批注，返回新 fid"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = self._conn.execute(f"""
            INSERT INTO {Constants.TABLE_NOTES} (
                {Constants.F_PROJECT_HASH}, {Constants.F_LAYER_ID}, {Constants.F_LAYER_NAME},
                {Constants.F_FEATURE_ID}, {Constants.F_NOTE_TEXT}, {Constants.F_STATUS},
                {Constants.F_PRIORITY}, {Constants.F_AUTHOR}, {Constants.F_TAGS},
                {Constants.F_GEOMETRY}, {Constants.F_CREATED_AT}, {Constants.F_UPDATED_AT}
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            note.project_hash, note.layer_id, note.layer_name,
            note.feature_id, note.note_text, note.status.value,
            note.priority.value, note.author, note.tags,
            note.geometry_wkt, now, now
        ))
        self._conn.commit()
        fid = cursor.lastrowid
        log_info(f"插入批注 #{fid}")
        return fid

    def update(self, note: ReviewNote) -> bool:
        """更新一条批注"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = self._conn.execute(f"""
            UPDATE {Constants.TABLE_NOTES} SET
                {Constants.F_NOTE_TEXT} = ?,
                {Constants.F_STATUS} = ?,
                {Constants.F_PRIORITY} = ?,
                {Constants.F_AUTHOR} = ?,
                {Constants.F_TAGS} = ?,
                {Constants.F_GEOMETRY} = ?,
                {Constants.F_UPDATED_AT} = ?
            WHERE {Constants.F_FID} = ?
        """, (
            note.note_text, note.status.value, note.priority.value,
            note.author, note.tags, note.geometry_wkt,
            now, note.fid
        ))
        self._conn.commit()
        return cursor.rowcount > 0

    def update_status(self, fid: int, status: ReviewStatus) -> bool:
        """仅更新状态"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = self._conn.execute(f"""
            UPDATE {Constants.TABLE_NOTES}
            SET {Constants.F_STATUS} = ?, {Constants.F_UPDATED_AT} = ?
            WHERE {Constants.F_FID} = ?
        """, (status.value, now, fid))
        self._conn.commit()
        return cursor.rowcount > 0

    def delete(self, fid: int) -> bool:
        """删除一条批注及其相关历史记录"""
        # 修改点：先删除对应的历史记录，防止产生“孤儿”数据
        self._conn.execute(
            f"DELETE FROM {Constants.TABLE_HISTORY} WHERE {Constants.F_HIST_NOTE_FID} = ?",
            (fid,)
        )

        # 再删除主表批注
        cursor = self._conn.execute(
            f"DELETE FROM {Constants.TABLE_NOTES} WHERE {Constants.F_FID} = ?",
            (fid,)
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def get_by_id(self, fid: int) -> Optional[ReviewNote]:
        """按 ID 查询单条批注"""
        cursor = self._conn.execute(f"""
            SELECT {Constants.F_FID}, {Constants.F_PROJECT_HASH},
                   {Constants.F_LAYER_ID}, {Constants.F_LAYER_NAME},
                   {Constants.F_FEATURE_ID}, {Constants.F_NOTE_TEXT},
                   {Constants.F_STATUS}, {Constants.F_PRIORITY},
                   {Constants.F_AUTHOR}, {Constants.F_TAGS},
                   {Constants.F_GEOMETRY}, {Constants.F_CREATED_AT},
                   {Constants.F_UPDATED_AT}
            FROM {Constants.TABLE_NOTES}
            WHERE {Constants.F_FID} = ?
        """, (fid,))
        row = cursor.fetchone()
        if row:
            return ReviewNote.from_db_row(tuple(row))
        return None

    def get_by_project(self, project_hash: str) -> List[ReviewNote]:
        """查询项目下所有批注"""
        cursor = self._conn.execute(f"""
            SELECT {Constants.F_FID}, {Constants.F_PROJECT_HASH},
                   {Constants.F_LAYER_ID}, {Constants.F_LAYER_NAME},
                   {Constants.F_FEATURE_ID}, {Constants.F_NOTE_TEXT},
                   {Constants.F_STATUS}, {Constants.F_PRIORITY},
                   {Constants.F_AUTHOR}, {Constants.F_TAGS},
                   {Constants.F_GEOMETRY}, {Constants.F_CREATED_AT},
                   {Constants.F_UPDATED_AT}
            FROM {Constants.TABLE_NOTES}
            WHERE {Constants.F_PROJECT_HASH} = ?
            ORDER BY {Constants.F_CREATED_AT} DESC
        """, (project_hash,))
        return [ReviewNote.from_db_row(tuple(r)) for r in cursor.fetchall()]

    def get_by_layer(self, project_hash: str, layer_id: str) -> List[ReviewNote]:
        cursor = self._conn.execute(f"""
            SELECT {Constants.F_FID}, {Constants.F_PROJECT_HASH},
                   {Constants.F_LAYER_ID}, {Constants.F_LAYER_NAME},
                   {Constants.F_FEATURE_ID}, {Constants.F_NOTE_TEXT},
                   {Constants.F_STATUS}, {Constants.F_PRIORITY},
                   {Constants.F_AUTHOR}, {Constants.F_TAGS},
                   {Constants.F_GEOMETRY}, {Constants.F_CREATED_AT},
                   {Constants.F_UPDATED_AT}
            FROM {Constants.TABLE_NOTES}
            WHERE {Constants.F_PROJECT_HASH} = ? AND {Constants.F_LAYER_ID} = ?
            ORDER BY {Constants.F_CREATED_AT} DESC
        """, (project_hash, layer_id))
        return [ReviewNote.from_db_row(tuple(r)) for r in cursor.fetchall()]

    def get_by_feature(self, project_hash: str, layer_id: str, feature_id: int) -> List[ReviewNote]:
        cursor = self._conn.execute(f"""
            SELECT {Constants.F_FID}, {Constants.F_PROJECT_HASH},
                   {Constants.F_LAYER_ID}, {Constants.F_LAYER_NAME},
                   {Constants.F_FEATURE_ID}, {Constants.F_NOTE_TEXT},
                   {Constants.F_STATUS}, {Constants.F_PRIORITY},
                   {Constants.F_AUTHOR}, {Constants.F_TAGS},
                   {Constants.F_GEOMETRY}, {Constants.F_CREATED_AT},
                   {Constants.F_UPDATED_AT}
            FROM {Constants.TABLE_NOTES}
            WHERE {Constants.F_PROJECT_HASH} = ? AND {Constants.F_LAYER_ID} = ?
                  AND {Constants.F_FEATURE_ID} = ?
            ORDER BY {Constants.F_CREATED_AT} DESC
        """, (project_hash, layer_id, feature_id))
        return [ReviewNote.from_db_row(tuple(r)) for r in cursor.fetchall()]

    def count_by_status(self, project_hash: str) -> dict:
        """按状态统计数量"""
        cursor = self._conn.execute(f"""
            SELECT {Constants.F_STATUS}, COUNT(*) as cnt
            FROM {Constants.TABLE_NOTES}
            WHERE {Constants.F_PROJECT_HASH} = ?
            GROUP BY {Constants.F_STATUS}
        """, (project_hash,))
        result = {"open": 0, "in_progress": 0, "resolved": 0, "wontfix": 0}
        for row in cursor.fetchall():
            key = row[0] if row[0] in result else "open"
            result[key] = row[1]
        return result

    def search(self, project_hash: str, status: str = "all",
               priorities: list = None, layer_id: str = "") -> List[ReviewNote]:
        """多条件筛选查询"""
        sql = f"""
            SELECT {Constants.F_FID}, {Constants.F_PROJECT_HASH},
                   {Constants.F_LAYER_ID}, {Constants.F_LAYER_NAME},
                   {Constants.F_FEATURE_ID}, {Constants.F_NOTE_TEXT},
                   {Constants.F_STATUS}, {Constants.F_PRIORITY},
                   {Constants.F_AUTHOR}, {Constants.F_TAGS},
                   {Constants.F_GEOMETRY}, {Constants.F_CREATED_AT},
                   {Constants.F_UPDATED_AT}
            FROM {Constants.TABLE_NOTES}
            WHERE {Constants.F_PROJECT_HASH} = ?
        """
        params = [project_hash]

        if status and status != "all":
            if status == "pending":
                status = "open"
            sql += f" AND {Constants.F_STATUS} = ?"
            params.append(status)

        if priorities:
            placeholders = ",".join("?" * len(priorities))
            sql += f" AND {Constants.F_PRIORITY} IN ({placeholders})"
            params.extend(priorities)

            # ---------- 替换图层过滤代码为以下内容 ----------
            if layer_id and str(layer_id).strip() != "all":
                actual_layer_name = layer_id

                # 尝试通过 QGIS 的 API 将乱码一样的 layer_id 翻译成直观的图层名称（例如"综合图层"）
                try:
                    from qgis.core import QgsProject
                    layer = QgsProject.instance().mapLayer(layer_id)
                    if layer:
                        actual_layer_name = layer.name()
                except Exception:
                    pass

                # 双重保险匹配：无论数据库里存的是底层 ID 还是 文本名称，只要对上一个就算命中！
                sql += f" AND ({Constants.F_LAYER_ID} = ? OR {Constants.F_LAYER_NAME} = ?)"
                params.extend([layer_id, actual_layer_name])

        sql += f" ORDER BY {Constants.F_CREATED_AT} DESC"

        cursor = self._conn.execute(sql, params)
        return [ReviewNote.from_db_row(tuple(r)) for r in cursor.fetchall()]

    def get_layer_names(self, project_hash: str) -> list:
        """获取项目下所有有批注的图层名"""
        cursor = self._conn.execute(f"""
            SELECT DISTINCT {Constants.F_LAYER_NAME}
            FROM {Constants.TABLE_NOTES}
            WHERE {Constants.F_PROJECT_HASH} = ? AND {Constants.F_LAYER_NAME} != ''
            ORDER BY {Constants.F_LAYER_NAME}
        """, (project_hash,))
        return [row[0] for row in cursor.fetchall()]

    def get_layer_ids(self, project_hash: str) -> list:
        """获取项目下所有有批注的图层 ID"""
        cursor = self._conn.execute(f"""
            SELECT DISTINCT {Constants.F_LAYER_ID}
            FROM {Constants.TABLE_NOTES}
            WHERE {Constants.F_PROJECT_HASH} = ?
            ORDER BY {Constants.F_LAYER_ID}
        """, (project_hash,))
        return [row[0] for row in cursor.fetchall()]

    def insert_history(self, note_fid: int, action: str, detail: str, operator: str) -> None:
        """插入一条历史记录"""
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._conn.execute(f"""
            INSERT INTO {Constants.TABLE_HISTORY} (
                {Constants.F_HIST_NOTE_FID}, {Constants.F_HIST_ACTION},
                {Constants.F_HIST_DETAIL}, {Constants.F_HIST_OPERATOR}, {Constants.F_HIST_CREATED}
            ) VALUES (?, ?, ?, ?, ?)
        """, (note_fid, action, detail, operator, now))
        self._conn.commit()

    def get_history(self, note_fid: int) -> list:
        """获取某条批注的所有历史记录"""
        cursor = self._conn.execute(f"""
            SELECT {Constants.F_HIST_ID}, {Constants.F_HIST_NOTE_FID},
                   {Constants.F_HIST_ACTION}, {Constants.F_HIST_DETAIL},
                   {Constants.F_HIST_OPERATOR}, {Constants.F_HIST_CREATED}
            FROM {Constants.TABLE_HISTORY}
            WHERE {Constants.F_HIST_NOTE_FID} = ?
            ORDER BY {Constants.F_HIST_CREATED} DESC
        """, (note_fid,))

        return [{
            "id": row[0],
            "note_fid": row[1],
            "action": row[2],
            "detail": row[3],
            "operator": row[4],
            "created_at": row[5]
        } for row in cursor.fetchall()]