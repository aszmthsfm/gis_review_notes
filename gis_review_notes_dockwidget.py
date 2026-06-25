# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GisReviewNotesDockWidget
                             -------------------
        begin                : 2026-06-22
        copyright            : (C) 2026 by zhangshun
        email                : 2023302051097@whu.edu.cn
 ***************************************************************************/
"""
import os
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import Qt, pyqtSignal, QModelIndex
from qgis.PyQt.QtWidgets import QHeaderView, QToolButton

# 导入新的表格模型和委托（你后续需要创建这两个文件）
try:
    from .ui.review_table_model import ReviewTableModel
    from .ui.review_delegate import ReviewItemDelegate
except ImportError:
    ReviewTableModel = None
    ReviewItemDelegate = None

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'gis_review_notes_dockwidget_base.ui'))


class GisReviewNotesDockWidget(QtWidgets.QDockWidget, FORM_CLASS):
    """GIS Review Notes 主界面 DockWidget"""

    closingPlugin = pyqtSignal()
    # ═══════════════════════════════════════════════════
    #  信号定义 — 供 Controller 连接
    # ═══════════════════════════════════════════════════
    add_note_requested = pyqtSignal()
    delete_note_requested = pyqtSignal(list)
    locate_feature_requested = pyqtSignal(int)
    mark_resolved_requested = pyqtSignal(int)
    export_report_requested = pyqtSignal()

    note_selected = pyqtSignal(int)
    note_double_clicked = pyqtSignal(int)

    edit_note_requested = pyqtSignal(int)
    copy_note_requested = pyqtSignal(int)
    note_history_requested = pyqtSignal(int)

    filter_changed = pyqtSignal(dict)
    refresh_requested = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        super(GisReviewNotesDockWidget, self).__init__(parent)
        self.setupUi(self)

        self._table_model = None
        self._current_fid = None
        self._filter_buttons_group = []

        self._init_table()
        self._init_filter_buttons()
        self._init_bottom_buttons()
        self._connect_signals()
        self._apply_styles()

    # ═══════════════════════════════════════════════════
    #  初始化各区域
    # ═══════════════════════════════════════════════════

    def _init_table(self):
        """初始化左侧批注列表表格"""
        if ReviewTableModel:
            self._table_model = ReviewTableModel()
            self.tableView_notes.setModel(self._table_model)
            self.tableView_notes.setItemDelegate(ReviewItemDelegate(self.tableView_notes))

        header = self.tableView_notes.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.Fixed)
            header.resizeSection(0, 50)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            header.setSectionResizeMode(2, QHeaderView.Fixed)
            header.resizeSection(2, 60)
            header.setSectionResizeMode(3, QHeaderView.Fixed)
            header.resizeSection(3, 50)
            header.setSectionResizeMode(4, QHeaderView.Fixed)
            header.resizeSection(4, 70)

        self.tableView_notes.verticalHeader().setVisible(False)

    def _init_filter_buttons(self):
        """初始化筛选按钮组 — 互斥选择"""
        self._filter_buttons_group = [
            self.toolButton_filterAll,
            self.toolButton_filterPending,
            self.toolButton_filterInProgress,
            self.toolButton_filterResolved,
        ]
        for btn in self._filter_buttons_group:
            btn.setAutoExclusive(True)

    def _init_bottom_buttons(self):
        """初始化底部操作按钮"""
        self.pushButton_addNote.setStyleSheet("""
            QPushButton {
                background-color: #2a7fff; color: white; font-weight: bold;
                border: none; padding: 6px 16px; border-radius: 3px;
            }
            QPushButton:hover { background-color: #1a6fef; }
            QPushButton:disabled { background-color: #aaa; }
        """)
        self._set_actions_enabled(False)

    def _connect_signals(self):
        """连接所有 UI 信号"""
        self.pushButton_addNote.clicked.connect(lambda: self.add_note_requested.emit())
        self.pushButton_deleteNote.clicked.connect(self._on_delete_note)
        self.pushButton_locateFeature.clicked.connect(self._on_locate_feature)
        self.pushButton_markResolved.clicked.connect(self._on_mark_resolved)
        self.pushButton_exportReport.clicked.connect(lambda: self.export_report_requested.emit())

        sel_model = self.tableView_notes.selectionModel()
        if sel_model:
            sel_model.selectionChanged.connect(self._on_table_selection_changed)
        self.tableView_notes.doubleClicked.connect(self._on_table_double_clicked)

        self.pushButton_editNote.clicked.connect(self._on_edit_note)
        self.pushButton_copyNote.clicked.connect(self._on_copy_note)
        self.pushButton_noteHistory.clicked.connect(self._on_note_history)

        for btn in self._filter_buttons_group:
            btn.clicked.connect(self._emit_filter_changed)

        self.toolButton_priCritical.clicked.connect(self._emit_filter_changed)
        self.toolButton_priHigh.clicked.connect(self._emit_filter_changed)
        self.toolButton_priMedium.clicked.connect(self._emit_filter_changed)
        self.toolButton_priLow.clicked.connect(self._emit_filter_changed)

        self.comboBox_layer.currentIndexChanged.connect(self._emit_filter_changed)
        self.checkBox_selectedOnly.stateChanged.connect(self._emit_filter_changed)
        self.pushButton_refresh.clicked.connect(lambda: self.refresh_requested.emit())

    def _apply_styles(self):
        self.setStyleSheet("""
            QFrame#frame_topBar, QFrame#frame_bottomBar {
                background-color: #f5f5f5; border: none; border-bottom: 1px solid #ddd;
            }
            QToolButton { padding: 3px 8px; border: 1px solid transparent; border-radius: 2px; }
            QToolButton:checked {
                background-color: #d0e3ff; border: 1px solid #2a7fff; font-weight: bold;
            }
        """)

    # ═══════════════════════════════════════════════════
    #  信号处理
    # ═══════════════════════════════════════════════════

    def _on_delete_note(self):
        sel_model = self.tableView_notes.selectionModel()
        if sel_model and sel_model.hasSelection():
            fids = []
            # 遍历所有选中的行
            for index in sel_model.selectedRows():
                fid = self._table_model.get_fid_at_row(index.row())
                if fid is not None:
                    fids.append(fid)
            # 如果有选中的 ID，则发射列表信号
            if fids:
                self.delete_note_requested.emit(fids)

    def _on_locate_feature(self):
        if self._current_fid is not None:
            self.locate_feature_requested.emit(self._current_fid)

    def _on_mark_resolved(self):
        if self._current_fid is not None:
            self.mark_resolved_requested.emit(self._current_fid)

    def _on_edit_note(self):
        if self._current_fid is not None:
            self.edit_note_requested.emit(self._current_fid)

    def _on_copy_note(self):
        if self._current_fid is not None:
            self.copy_note_requested.emit(self._current_fid)

    def _on_note_history(self):
        if self._current_fid is not None:
            self.note_history_requested.emit(self._current_fid)

    def _on_table_selection_changed(self):
        index = self.tableView_notes.currentIndex()
        if not index.isValid() or self._table_model is None:
            self._current_fid = None
            self._clear_detail()
            self._set_actions_enabled(False)
            return

        fid = self._table_model.get_fid_at_row(index.row())
        self._current_fid = fid
        note = self._table_model.get_note_at_row(index.row())
        if note:
            self._populate_detail(note)
            self._set_actions_enabled(True)
            self.note_selected.emit(fid)

    def _on_table_double_clicked(self, index: QModelIndex):
        if index.isValid() and self._table_model:
            fid = self._table_model.get_fid_at_row(index.row())
            self.note_double_clicked.emit(fid)

    def _emit_filter_changed(self):
        self.filter_changed.emit(self.get_current_filters())

    # ═══════════════════════════════════════════════════
    #  外部调用接口
    # ═══════════════════════════════════════════════════

    def refresh_table(self, notes):
        if self._table_model:
            self._table_model.set_notes(notes)
            self.label_count.setText(f"共 {len(notes)} 条")
            self._clear_detail()

    def update_statistics(self, stats: dict):
        self.label_stats.setText(
            f"待处理 {stats.get('pending', 0)} | "
            f"处理中 {stats.get('in_progress', 0)} | "
            f"已完成 {stats.get('resolved', 0)}"
        )

    def update_layer_combo(self, layer_names: list):
        self.comboBox_layer.blockSignals(True)
        self.comboBox_layer.clear()
        self.comboBox_layer.addItem("全部图层", "")
        for name in layer_names:
            self.comboBox_layer.addItem(name, name)
        self.comboBox_layer.blockSignals(False)

    def get_current_filters(self) -> dict:
        status = "all"
        if self.toolButton_filterPending.isChecked():
            status = "pending"
        elif self.toolButton_filterInProgress.isChecked():
            status = "in_progress"
        elif self.toolButton_filterResolved.isChecked():
            status = "resolved"

        priorities = []
        if self.toolButton_priCritical.isChecked(): priorities.append(4)  # CRITICAL
        if self.toolButton_priHigh.isChecked(): priorities.append(3)  # HIGH
        if self.toolButton_priMedium.isChecked(): priorities.append(2)  # MEDIUM
        if self.toolButton_priLow.isChecked(): priorities.append(1)  # LOW

        return {
            "status": status,
            "priorities": priorities,
            "layer": self.comboBox_layer.currentData() or "",
            "selected_only": self.checkBox_selectedOnly.isChecked(),
        }

    def show_message(self, message: str, level: str = "info"):
        color_map = {"info": "#333", "warning": "#cc8800", "error": "#cc0000", "success": "#008800"}
        self.label_stats.setTextFormat(Qt.RichText)
        self.label_stats.setText(f'<span style="color:{color_map.get(level, "#333")}">{message}</span>')

    # ═══════════════════════════════════════════════════
    #  辅助方法
    # ═══════════════════════════════════════════════════

    def _populate_detail(self, note):
        self.label_detailId.setText(f"#{note.fid}")
        self.label_detailLayer.setText(note.layer_name)
        self.label_detailFeatureId.setText(str(note.feature_id))

        # 简单展示优先级和状态，后续可丰富颜色
        self.label_detailPriority.setText(str(note.priority.name if hasattr(note.priority, 'name') else note.priority))
        self.label_detailStatus.setText(str(note.status.name if hasattr(note.status, 'name') else note.status))

        self.label_detailAuthor.setText(note.author or "--")
        self.label_detailTags.setText(note.tags or "--")

        created = note.created_at.strftime("%Y-%m-%d %H:%M") if note.created_at else "--"
        updated = note.updated_at.strftime("%Y-%m-%d %H:%M") if note.updated_at else "--"
        self.label_detailCreated.setText(created)
        self.label_detailUpdated.setText(updated)

        self.plainTextEdit_noteContent.setPlainText(note.note_text or "")

    def _clear_detail(self):
        self.label_detailId.setText("#--")
        for lbl in [self.label_detailLayer, self.label_detailFeatureId, self.label_detailPriority,
                    self.label_detailStatus, self.label_detailAuthor, self.label_detailTags,
                    self.label_detailCreated, self.label_detailUpdated]:
            lbl.setText("--")
        self.plainTextEdit_noteContent.clear()

    def _set_actions_enabled(self, enabled: bool):
        self.pushButton_deleteNote.setEnabled(enabled)
        self.pushButton_locateFeature.setEnabled(enabled)
        self.pushButton_markResolved.setEnabled(enabled)
        self.pushButton_editNote.setEnabled(enabled)
        self.pushButton_copyNote.setEnabled(enabled)
        self.pushButton_noteHistory.setEnabled(enabled)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()
