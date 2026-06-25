# -*- coding: utf-8 -*-
"""全局常量定义"""


class Constants:
    """所有全局常量集中管理"""

    # ═══════════════════════════════════════
    #  GeoPackage 表名
    # ═══════════════════════════════════════

    TABLE_NOTES = "review_notes"
    TABLE_BINDINGS = "project_bindings"
    TABLE_META = "schema_meta"

    # ═══════════════════════════════════════
    #  review_notes 字段名
    # ═══════════════════════════════════════

    F_FID = "fid"
    F_PROJECT_HASH = "project_hash"
    F_LAYER_ID = "layer_id"
    F_LAYER_NAME = "source_layer_name"
    F_FEATURE_ID = "feature_id"
    F_NOTE_TEXT = "note_text"
    F_STATUS = "status"
    F_PRIORITY = "priority"
    F_AUTHOR = "author"
    F_TAGS = "tags"
    F_GEOMETRY = "geometry"
    F_CREATED_AT = "created_at"
    F_UPDATED_AT = "updated_at"

    # ═══════════════════════════════════════
    #  project_bindings 字段名
    # ═══════════════════════════════════════

    F_BINDING_FID = "fid"
    F_BINDING_HASH = "project_hash"
    F_BINDING_PATH = "project_path"
    F_BINDING_GPKG = "gpkg_path"
    F_BINDING_TITLE = "project_title"
    F_BINDING_CREATED = "created_at"
    F_BINDING_LAST_OPENED = "last_opened"

    # ═══════════════════════════════════════
    #  schema_meta 键名
    # ═══════════════════════════════════════

    META_SCHEMA_VERSION = "schema_version"
    META_PLUGIN_VERSION = "plugin_version"
    META_CREATED_AT = "created_at"

    # ═══════════════════════════════════════
    #  默认值
    # ═══════════════════════════════════════

    DEFAULT_GPKG_DIR = "gis_review_notes"
    SCHEMA_VERSION = 1
    PLUGIN_VERSION = "0.1.0"
    DEFAULT_SRS_ID = 4326

    # ═══════════════════════════════════════
    #  内存标注图层
    # ═══════════════════════════════════════

    OVERLAY_LAYER_NAME = "_gis_review_notes_overlay"
    OVERLAY_LAYER_TYPE = "Point"


    # ═══════════════════════════════════════
    #  历史记录表名与字段
    # ═══════════════════════════════════════

    TABLE_HISTORY = "review_notes_history"
    F_HIST_ID = "id"
    F_HIST_NOTE_FID = "note_fid"
    F_HIST_ACTION = "action"
    F_HIST_DETAIL = "detail"
    F_HIST_OPERATOR = "operator"
    F_HIST_CREATED = "created_at"