# -*- coding: utf-8 -*-
"""项目绑定关系 DAO"""

from datetime import datetime
from typing import Optional
from ..core.models import ProjectBinding
from ..core.constants import Constants
from .connection_manager import ConnectionManager


class ProjectMetaRepository:
    """项目与 GPKG 绑定关系的 CRUD"""

    def __init__(self, conn_manager: ConnectionManager):
        self._conn_manager = conn_manager

    @property
    def _conn(self):
        return self._conn_manager.get_connection()

    def upsert(self, binding: ProjectBinding) -> int:
        """插入或更新绑定关系"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = self._conn.execute(f"""
            INSERT INTO {Constants.TABLE_BINDINGS} (
                {Constants.F_BINDING_HASH}, {Constants.F_BINDING_PATH},
                {Constants.F_BINDING_GPKG}, {Constants.F_BINDING_TITLE},
                {Constants.F_BINDING_CREATED}, {Constants.F_BINDING_LAST_OPENED}
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT({Constants.F_BINDING_HASH}) DO UPDATE SET
                {Constants.F_BINDING_PATH} = excluded.{Constants.F_BINDING_PATH},
                {Constants.F_BINDING_GPKG} = excluded.{Constants.F_BINDING_GPKG},
                {Constants.F_BINDING_TITLE} = excluded.{Constants.F_BINDING_TITLE},
                {Constants.F_BINDING_LAST_OPENED} = excluded.{Constants.F_BINDING_LAST_OPENED}
        """, (
            binding.project_hash, binding.project_path,
            binding.gpkg_path, binding.project_title,
            now, now
        ))
        self._conn.commit()
        return cursor.lastrowid

    def get_by_hash(self, project_hash: str) -> Optional[ProjectBinding]:
        cursor = self._conn.execute(f"""
            SELECT {Constants.F_BINDING_FID}, {Constants.F_BINDING_HASH},
                   {Constants.F_BINDING_PATH}, {Constants.F_BINDING_GPKG},
                   {Constants.F_BINDING_TITLE}, {Constants.F_BINDING_CREATED},
                   {Constants.F_BINDING_LAST_OPENED}
            FROM {Constants.TABLE_BINDINGS}
            WHERE {Constants.F_BINDING_HASH} = ?
        """, (project_hash,))
        row = cursor.fetchone()
        if not row:
            return None

        def parse_dt(val):
            if not val:
                return None
            try:
                return datetime.fromisoformat(str(val))
            except (ValueError, TypeError):
                try:
                    return datetime.strptime(str(val), "%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError):
                    return None

        return ProjectBinding(
            fid=row[0],
            project_hash=row[1] or "",
            project_path=row[2] or "",
            gpkg_path=row[3] or "",
            project_title=row[4] or "",
            created_at=parse_dt(row[5]),
            last_opened=parse_dt(row[6]),
        )

    def update_last_opened(self, project_hash: str) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._conn.execute(f"""
            UPDATE {Constants.TABLE_BINDINGS}
            SET {Constants.F_BINDING_LAST_OPENED} = ?
            WHERE {Constants.F_BINDING_HASH} = ?
        """, (now, project_hash))
        self._conn.commit()
