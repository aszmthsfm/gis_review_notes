# -*- coding: utf-8 -*-
"""历史记录查看对话框"""

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView
)
from qgis.PyQt.QtCore import Qt


class HistoryDialog(QDialog):
    """展示批注操作历史的对话框"""

    def __init__(self, note_fid: int, history_data: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"批注 #{note_fid} - 操作历史")
        self.resize(550, 300)
        self.history_data = history_data
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self.table = QTableWidget(len(self.history_data), 4)
        self.table.setHorizontalHeaderLabels(["时间", "操作者", "操作类型", "详细信息"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)

        for row, item in enumerate(self.history_data):
            self.table.setItem(row, 0, QTableWidgetItem(str(item["created_at"])))
            self.table.setItem(row, 1, QTableWidgetItem(str(item["operator"])))
            self.table.setItem(row, 2, QTableWidgetItem(str(item["action"])))
            self.table.setItem(row, 3, QTableWidgetItem(str(item["detail"])))

        layout.addWidget(self.table)