# -*- coding: utf-8 -*-
"""SQLite 连接管理器（单例模式）"""

import sqlite3
from ..utils.logger import log_info, log_error


class ConnectionManager:
    """管理 GeoPackage 的 SQLite 连接，全局单例"""

    _instance = None

    def __init__(self):
        self._gpkg_path: str = ""
        self._connection: sqlite3.Connection | None = None

    @classmethod
    def instance(cls) -> "ConnectionManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_connection(self) -> sqlite3.Connection:
        """获取当前连接，若不存在则自动创建"""
        if self._connection is None and self._gpkg_path:
            self._connection = sqlite3.connect(self._gpkg_path)
            self._connection.row_factory = sqlite3.Row
            # 启用外键约束
            self._connection.execute("PRAGMA foreign_keys = ON")
            log_info(f"数据库连接已建立: {self._gpkg_path}")
        return self._connection

    def switch_gpkg(self, gpkg_path: str) -> None:
        """切换到新的 GPKG 文件"""
        if self._gpkg_path == gpkg_path and self._connection is not None:
            return
        self.close()
        self._gpkg_path = gpkg_path
        self._connection = sqlite3.connect(gpkg_path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        log_info(f"已切换数据库: {gpkg_path}")

    @property
    def gpkg_path(self) -> str:
        return self._gpkg_path

    def close(self) -> None:
        """关闭连接"""
        if self._connection:
            try:
                self._connection.close()
            except Exception as e:
                log_error(f"关闭数据库连接时出错: {e}")
            finally:
                self._connection = None
