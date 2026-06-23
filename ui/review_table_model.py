# -*- coding: utf-8 -*-
"""批注列表表格数据模型"""

from qgis.PyQt.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant
from qgis.PyQt.QtGui import QColor, QFont

from ..core.models import ReviewNote
from ..core.enums import (
    ReviewStatus, NotePriority,
    STATUS_DISPLAY, PRIORITY_DISPLAY
)


class ReviewTableModel(QAbstractTableModel):
    """QTableView 的数据模型"""

    COLUMNS = [
        ("ID",     "fid"),
        ("图层",   "layer_name"),
        ("要素ID", "feature_id"),
        ("优先级", "priority"),
        ("状态",   "status"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._notes: list[ReviewNote] = []

    # ── 数据源 ──
    def set_notes(self, notes):
        self.beginResetModel()
        self._notes = list(notes)
        self.endResetModel()

    def get_note_at_row(self, row):
        if 0 <= row < len(self._notes):
            return self._notes[row]
        return None

    def get_fid_at_row(self, row):
        note = self.get_note_at_row(row)
        return note.fid if note else None

    def find_row_by_fid(self, fid):
        for i, note in enumerate(self._notes):
            if note.fid == fid:
                return i
        return -1

    # ── QAbstractTableModel ──
    def rowCount(self, parent=QModelIndex()):
        return len(self._notes)

    def columnCount(self, parent=QModelIndex()):
        return len(self.COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()

        note = self._notes[index.row()]
        col_key = self.COLUMNS[index.column()][1]

        if role == Qt.DisplayRole:
            if col_key == "fid":
                return f"#{note.fid}"
            elif col_key == "layer_name":
                return note.layer_name
            elif col_key == "feature_id":
                return str(note.feature_id)
            elif col_key == "priority":
                return PRIORITY_DISPLAY.get(note.priority, "--")
            elif col_key == "status":
                return STATUS_DISPLAY.get(note.status, "--")

        elif role == Qt.UserRole:
            return note

        elif role == Qt.TextAlignmentRole:
            if col_key in ("fid", "feature_id", "priority", "status"):
                return Qt.AlignCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        elif role == Qt.ForegroundRole:
            if col_key == "priority":
                colors = {
                    NotePriority.CRITICAL: QColor("#cc0000"),
                    NotePriority.HIGH:     QColor("#cc6600"),
                    NotePriority.MEDIUM:   QColor("#0066cc"),
                    NotePriority.LOW:      QColor("#666666"),
                }
                return colors.get(note.priority, QColor("#333"))
            if col_key == "status":
                colors = {
                    ReviewStatus.OPEN:        QColor("#cc0000"),
                    ReviewStatus.IN_PROGRESS: QColor("#cc8800"),
                    ReviewStatus.RESOLVED:    QColor("#008800"),
                    ReviewStatus.WONTFIX:     QColor("#666666"),
                }
                return colors.get(note.status, QColor("#333"))

        elif role == Qt.FontRole:
            if col_key == "priority" and note.priority == NotePriority.CRITICAL:
                font = QFont()
                font.setBold(True)
                return font

        return QVariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.COLUMNS[section][0]
        return QVariant()

    def sort(self, column, order=Qt.AscendingOrder):
        if column < 0 or column >= len(self.COLUMNS):
            return
        col_key = self.COLUMNS[column][1]
        reverse = (order == Qt.DescendingOrder)
        self.layoutAboutToBeChanged.emit()

        def sort_key(n):
            val = getattr(n, col_key, 0)
            if isinstance(val, (ReviewStatus, NotePriority)):
                return val.value
            return val

        self._notes.sort(key=sort_key, reverse=reverse)
        self.layoutChanged.emit()
