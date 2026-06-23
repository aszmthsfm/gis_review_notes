# -*- coding: utf-8 -*-
"""添加/编辑批注对话框"""

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QPlainTextEdit,
    QComboBox, QLineEdit, QDialogButtonBox, QLabel
)
from qgis.PyQt.QtCore import Qt

from ..core.enums import NotePriority, PRIORITY_DISPLAY, ReviewStatus, STATUS_DISPLAY
from ..core.models import ReviewNote


class NoteEditDialog(QDialog):
    """添加或编辑审查批注的对话框"""

    def __init__(self, note: ReviewNote = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑批注" if note else "添加批注")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)

        self._note = note
        self._setup_ui()
        if note:
            self._populate(note)

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # 要素信息标签
        self.label_info = QLabel("要素信息: --")
        self.label_info.setStyleSheet("color: #666; padding: 4px;")
        layout.addWidget(self.label_info)

        # 表单
        form = QFormLayout()

        self.combo_priority = QComboBox()
        for p in [NotePriority.LOW, NotePriority.MEDIUM, NotePriority.HIGH, NotePriority.CRITICAL]:
            self.combo_priority.addItem(PRIORITY_DISPLAY[p], p)
        form.addRow("优先级:", self.combo_priority)

        self.combo_status = QComboBox()
        for s in [ReviewStatus.OPEN, ReviewStatus.IN_PROGRESS, ReviewStatus.RESOLVED, ReviewStatus.WONTFIX]:
            self.combo_status.addItem(STATUS_DISPLAY[s], s)
        form.addRow("状态:", self.combo_status)

        self.edit_author = QLineEdit()
        self.edit_author.setPlaceholderText("输入审查人姓名")
        form.addRow("作者:", self.edit_author)

        self.edit_tags = QLineEdit()
        self.edit_tags.setPlaceholderText("多个标签用逗号分隔")
        form.addRow("标签:", self.edit_tags)

        layout.addLayout(form)

        # 审查意见
        layout.addWidget(QLabel("审查意见:"))
        self.edit_note = QPlainTextEdit()
        self.edit_note.setPlaceholderText("请输入审查意见内容...")
        layout.addWidget(self.edit_note)

        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate(self, note: ReviewNote):
        self.label_info.setText(
            f"要素信息: {note.layer_name} / FID:{note.feature_id}"
        )
        self.edit_note.setPlainText(note.note_text)
        self.edit_author.setText(note.author)
        self.edit_tags.setText(note.tags)

        idx = self.combo_priority.findData(note.priority)
        if idx >= 0:
            self.combo_priority.setCurrentIndex(idx)

        idx = self.combo_status.findData(note.status)
        if idx >= 0:
            self.combo_status.setCurrentIndex(idx)

    def set_feature_info(self, layer_name: str, feature_id: int):
        """设置要素信息（添加模式）"""
        self.label_info.setText(f"要素信息: {layer_name} / FID:{feature_id}")

    def get_values(self) -> dict:
        """获取对话框中的值"""
        return {
            "note_text": self.edit_note.toPlainText().strip(),
            "priority": self.combo_priority.currentData(),
            "status": self.combo_status.currentData(),
            "author": self.edit_author.text().strip(),
            "tags": self.edit_tags.text().strip(),
        }
