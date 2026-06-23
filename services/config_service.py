# -*- coding: utf-8 -*-
"""配置服务，封装 QSettings 读写"""

from qgis.core import QgsSettings


class ConfigService:
    """读写插件配置"""

    SETTINGS_PREFIX = "gis_review_notes"

    def __init__(self):
        self._settings = QgsSettings()

    def get(self, key: str, default=None):
        full_key = f"{self.SETTINGS_PREFIX}/{key}"
        return self._settings.value(full_key, default)

    def set(self, key: str, value):
        full_key = f"{self.SETTINGS_PREFIX}/{key}"
        self._settings.setValue(full_key, value)

    def get_gpkg_path(self) -> str:
        return self.get("gpkg_path", "")

    def set_gpkg_path(self, path: str):
        self.set("gpkg_path", path)

    def get_default_author(self) -> str:
        return self.get("author", "")

    def set_default_author(self, author: str):
        self.set("author", author)
