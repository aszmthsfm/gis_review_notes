# -*- coding: utf-8 -*-
"""表格委托：状态/优先级渲染"""

from qgis.PyQt.QtWidgets import QStyledItemDelegate, QStyle
from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QColor, QPainter, QBrush


class ReviewItemDelegate(QStyledItemDelegate):
    """自定义委托：为优先级和状态列绘制颜色标签"""

    def paint(self, painter, option, index):
        col_key = index.model().COLUMNS[index.column()][1]

        if col_key == "priority":
            self._paint_priority(painter, option, index)
        elif col_key == "status":
            self._paint_status(painter, option, index)
        else:
            super().paint(painter, option, index)

    def _paint_priority(self, painter, option, index):
        """绘制优先级圆点"""
        note = index.data(Qt.UserRole)
        if not note:
            super().paint(painter, option, index)
            return

        from ..core.enums import NotePriority, PRIORITY_DISPLAY

        colors = {
            NotePriority.CRITICAL: QColor("#cc0000"),
            NotePriority.HIGH:     QColor("#cc6600"),
            NotePriority.MEDIUM:   QColor("#0066cc"),
            NotePriority.LOW:      QColor("#666666"),
        }

        color = colors.get(note.priority, QColor("#666"))
        text = PRIORITY_DISPLAY.get(note.priority, "--")

        # 绘制背景
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        else:
            painter.fillRect(option.rect, option.palette.base())

        # 绘制圆点
        dot_x = option.rect.left() + 8
        dot_y = option.rect.center().y()
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(dot_x - 4, dot_y - 4, 8, 8)

        # 绘制文字
        painter.setPen(option.palette.text().color())
        text_rect = option.rect.adjusted(18, 0, 0, 0)
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, text)

    def _paint_status(self, painter, option, index):
        """绘制状态标签"""
        note = index.data(Qt.UserRole)
        if not note:
            super().paint(painter, option, index)
            return

        from ..core.enums import ReviewStatus, STATUS_DISPLAY

        bg_colors = {
            ReviewStatus.OPEN:        QColor(255, 235, 238),
            ReviewStatus.IN_PROGRESS: QColor(255, 243, 224),
            ReviewStatus.RESOLVED:    QColor(232, 245, 233),
            ReviewStatus.WONTFIX:     QColor(245, 245, 245),
        }
        text_colors = {
            ReviewStatus.OPEN:        QColor("#cc0000"),
            ReviewStatus.IN_PROGRESS: QColor("#cc8800"),
            ReviewStatus.RESOLVED:    QColor("#008800"),
            ReviewStatus.WONTFIX:     QColor("#666666"),
        }

        bg = bg_colors.get(note.status, QColor(245, 245, 245))
        fg = text_colors.get(note.status, QColor("#333"))
        text = STATUS_DISPLAY.get(note.status, "--")

        # 选中状态
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            painter.setPen(option.palette.highlightedText().color())
        else:
            # 绘制圆角背景
            rect = option.rect.adjusted(4, 4, -4, -4)
            painter.setBrush(QBrush(bg))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect, 3, 3)
            painter.setPen(fg)

        text_rect = option.rect.adjusted(0, 0, 0, 0)
        painter.drawText(text_rect, Qt.AlignCenter, text)

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), 28)
