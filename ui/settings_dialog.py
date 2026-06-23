# -*- coding: utf-8 -*-
"""设置对话框（占位，后续完善）"""

from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QDialogButtonBox


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, config_service, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GIS Review Notes 设置")
        self._config = config_service
        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.edit_author = QLineEdit()
        self.edit_author.setPlaceholderText("默认审查人姓名")
        form.addRow("默认作者:", self.edit_author)

        self.edit_gpkg = QLineEdit()
        self.edit_gpkg.setPlaceholderText("GeoPackage 文件路径（留空则使用默认路径）")
        form.addRow("GPKG 路径:", self.edit_gpkg)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=self
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_values(self):
        self.edit_author.setText(self._config.get_default_author())
        self.edit_gpkg.setText(self._config.get_gpkg_path())

    def _save_and_accept(self):
        self._config.set_default_author(self.edit_author.text().strip())
        self._config.set_gpkg_path(self.edit_gpkg.text().strip())
        self.accept()
