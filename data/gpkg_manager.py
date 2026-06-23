# -*- coding: utf-8 -*-
"""GeoPackage 数据库管理：建库、建表、迁移"""

import os
import sqlite3
from ..core.constants import Constants
from ..utils.logger import log_info, log_error


class GpkgManager:
    """负责 GeoPackage 文件的创建、schema 初始化和版本迁移"""

    def __init__(self, gpkg_path: str):
        self.gpkg_path = gpkg_path

    def init_or_migrate(self) -> None:
        """初始化或迁移数据库"""
        need_create = not os.path.exists(self.gpkg_path)

        conn = sqlite3.connect(self.gpkg_path)
        try:
            if need_create:
                self._create_gpkg_base(conn)
                log_info(f"创建新 GeoPackage: {self.gpkg_path}")

            self._create_tables(conn)
            self._create_indexes(conn)
            self._ensure_meta(conn)
            conn.commit()
            log_info("数据库初始化/迁移完成")
        except Exception as e:
            log_error(f"数据库初始化失败: {e}")
            raise
        finally:
            conn.close()

    def _create_gpkg_base(self, conn: sqlite3.Connection) -> None:
        """创建 GeoPackage 基础元数据表"""
        # gpkg_spatial_ref_sys
        conn.execute("""
            CREATE TABLE IF NOT EXISTS gpkg_spatial_ref_sys (
                srs_name TEXT NOT NULL,
                srs_id INTEGER NOT NULL PRIMARY KEY,
                organization TEXT NOT NULL,
                organization_coordsys_id INTEGER NOT NULL,
                definition TEXT NOT NULL,
                description TEXT
            )
        """)

        # 插入 EPSG:4326
        conn.execute("""
            INSERT OR IGNORE INTO gpkg_spatial_ref_sys
            (srs_name, srs_id, organization, organization_coordsys_id, definition, description)
            VALUES ('WGS 84 geodetic', 4326, 'EPSG', 4326,
                    'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]',
                    'WGS 84')
        """)

        # 插入 -1 占位
        conn.execute("""
            INSERT OR IGNORE INTO gpkg_spatial_ref_sys
            (srs_name, srs_id, organization, organization_coordsys_id, definition, description)
            VALUES ('Undefined cartesian', -1, 'NONE', -1, 'undefined', 'undefined')
        """)

        # gpkg_contents
        conn.execute("""
            CREATE TABLE IF NOT EXISTS gpkg_contents (
                table_name TEXT NOT NULL PRIMARY KEY,
                data_type TEXT NOT NULL,
                identifier TEXT,
                description TEXT,
                last_change DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                min_x DOUBLE,
                min_y DOUBLE,
                max_x DOUBLE,
                max_y DOUBLE,
                srs_id INTEGER
            )
        """)

        # gpkg_geometry_columns
        conn.execute("""
            CREATE TABLE IF NOT EXISTS gpkg_geometry_columns (
                table_name TEXT NOT NULL,
                column_name TEXT NOT NULL,
                geometry_type_name TEXT NOT NULL,
                srs_id INTEGER NOT NULL,
                z TINYINT NOT NULL,
                m TINYINT NOT NULL,
                CONSTRAINT pk_geom_cols PRIMARY KEY (table_name, column_name),
                CONSTRAINT uk_gc_table_name UNIQUE (table_name)
            )
        """)

        # 应用注册表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS gpkg_extensions (
                table_name TEXT,
                column_name TEXT,
                extension_name TEXT NOT NULL,
                definition TEXT NOT NULL,
                scope TEXT NOT NULL
            )
        """)

    def _create_tables(self, conn: sqlite3.Connection) -> None:
        """创建业务表"""

        # review_notes 表
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {Constants.TABLE_NOTES} (
                {Constants.F_FID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {Constants.F_PROJECT_HASH} TEXT NOT NULL,
                {Constants.F_LAYER_ID} TEXT NOT NULL,
                {Constants.F_LAYER_NAME} TEXT DEFAULT '',
                {Constants.F_FEATURE_ID} INTEGER NOT NULL,
                {Constants.F_NOTE_TEXT} TEXT NOT NULL DEFAULT '',
                {Constants.F_STATUS} TEXT NOT NULL DEFAULT 'open',
                {Constants.F_PRIORITY} INTEGER NOT NULL DEFAULT 2,
                {Constants.F_AUTHOR} TEXT DEFAULT '',
                {Constants.F_TAGS} TEXT DEFAULT '',
                {Constants.F_GEOMETRY} TEXT DEFAULT '',
                {Constants.F_CREATED_AT} TEXT NOT NULL DEFAULT (datetime('now')),
                {Constants.F_UPDATED_AT} TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        # 注册到 gpkg_contents
        conn.execute(f"""
            INSERT OR IGNORE INTO gpkg_contents
            (table_name, data_type, identifier, description, srs_id)
            VALUES ('{Constants.TABLE_NOTES}', 'features', 'Review Notes',
                    'GIS Review Notes annotations', {Constants.DEFAULT_SRS_ID})
        """)

        # 注册到 gpkg_geometry_columns
        conn.execute(f"""
            INSERT OR IGNORE INTO gpkg_geometry_columns
            (table_name, column_name, geometry_type_name, srs_id, z, m)
            VALUES ('{Constants.TABLE_NOTES}', '{Constants.F_GEOMETRY}', 'POINT',
                    {Constants.DEFAULT_SRS_ID}, 0, 0)
        """)

        # project_bindings 表
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {Constants.TABLE_BINDINGS} (
                {Constants.F_BINDING_FID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {Constants.F_BINDING_HASH} TEXT UNIQUE NOT NULL,
                {Constants.F_BINDING_PATH} TEXT NOT NULL,
                {Constants.F_BINDING_GPKG} TEXT NOT NULL,
                {Constants.F_BINDING_TITLE} TEXT DEFAULT '',
                {Constants.F_BINDING_CREATED} TEXT NOT NULL DEFAULT (datetime('now')),
                {Constants.F_BINDING_LAST_OPENED} TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        # schema_meta 表
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {Constants.TABLE_META} (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

    def _create_indexes(self, conn: sqlite3.Connection) -> None:
        """创建索引"""
        indexes = [
            f"CREATE INDEX IF NOT EXISTS idx_notes_project ON {Constants.TABLE_NOTES}({Constants.F_PROJECT_HASH})",
            f"CREATE INDEX IF NOT EXISTS idx_notes_layer ON {Constants.TABLE_NOTES}({Constants.F_PROJECT_HASH}, {Constants.F_LAYER_ID})",
            f"CREATE INDEX IF NOT EXISTS idx_notes_feature ON {Constants.TABLE_NOTES}({Constants.F_PROJECT_HASH}, {Constants.F_LAYER_ID}, {Constants.F_FEATURE_ID})",
            f"CREATE INDEX IF NOT EXISTS idx_notes_status ON {Constants.TABLE_NOTES}({Constants.F_PROJECT_HASH}, {Constants.F_STATUS})",
            f"CREATE INDEX IF NOT EXISTS idx_notes_priority ON {Constants.TABLE_NOTES}({Constants.F_PROJECT_HASH}, {Constants.F_PRIORITY})",
        ]
        for sql in indexes:
            conn.execute(sql)

    def _ensure_meta(self, conn: sqlite3.Connection) -> None:
        """写入 schema 版本信息"""
        conn.execute(f"""
            INSERT OR IGNORE INTO {Constants.TABLE_META} (key, value)
            VALUES ('{Constants.META_SCHEMA_VERSION}', '{Constants.SCHEMA_VERSION}')
        """)
        conn.execute(f"""
            INSERT OR IGNORE INTO {Constants.TABLE_META} (key, value)
            VALUES ('{Constants.META_PLUGIN_VERSION}', '{Constants.PLUGIN_VERSION}')
        """)
