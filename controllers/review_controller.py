# -*- coding: utf-8 -*-
"""主控制器：连接 DockWidget UI 与 Service 层"""

import os

from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.PyQt.QtWidgets import QMessageBox, QFileDialog
from qgis.core import QgsProject, QgsVectorLayer, Qgis
from qgis.PyQt.QtWidgets import QAbstractItemView

from ..core.enums import ReviewStatus, NotePriority
from ..core.models import ReviewNote
from ..ui.note_edit_dialog import NoteEditDialog
from ..utils.logger import log_info, log_error


class ReviewController(QObject):
    """连接 UI 和 Service，管理状态机"""

    status_message = pyqtSignal(str, str)  # message, level

    def __init__(self, dock_widget, note_service, selection_service,
                 render_service, export_service):
        super().__init__()
        self.dock = dock_widget
        self.note_service = note_service
        self.selection_service = selection_service
        self.render_service = render_service
        self.export_service = export_service

        # 仅当 dock 不为空时才在初始化时连接
        if self.dock is not None:
            self._connect_dock_signals()

    def set_dock_widget(self, dock_widget):
        """后期注入 DockWidget 并连接信号"""
        self.dock = dock_widget
        self.dock.tableView_notes.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.dock.tableView_notes.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._connect_dock_signals()


    def _connect_dock_signals(self):
        """连接 DockWidget 的所有信号"""
        # 底部操作栏
        self.dock.add_note_requested.connect(self._on_add_note)
        self.dock.delete_note_requested.connect(self._on_delete_note)
        self.dock.locate_feature_requested.connect(self._on_locate_feature)
        self.dock.mark_resolved_requested.connect(self._on_mark_resolved)
        self.dock.export_report_requested.connect(self._on_export_report)

        # 表格交互
        self.dock.note_selected.connect(self._on_note_selected)
        self.dock.note_double_clicked.connect(self._on_note_double_clicked)

        # 详情区操作
        self.dock.edit_note_requested.connect(self._on_edit_note)
        self.dock.copy_note_requested.connect(self._on_copy_note)
        self.dock.note_history_requested.connect(self._on_note_history)

        # 筛选
        self.dock.filter_changed.connect(self._on_filter_changed)
        self.dock.refresh_requested.connect(self._on_refresh)

    # ═══════════════════════════════════════
    #  生命周期
    # ═══════════════════════════════════════

    def initialize(self):
        """项目加载后初始化"""
        try:
            self.note_service.update_project_hash()
            self._refresh_all()
            log_info("ReviewController 初始化完成")
        except Exception as e:
            log_error(f"初始化失败: {e}")

    def on_project_saved(self):
        """项目保存后重新加载"""
        self.note_service.update_project_hash()
        self._refresh_all()

    def cleanup(self):
        """清理资源"""
        pass

    # ═══════════════════════════════════════
    #  底部操作栏处理
    # ═══════════════════════════════════════

    def _on_add_note(self):
        """添加批注（支持单个或多个选中要素）"""
        # 1. 获取所有选中的要素
        selected_features = self.selection_service.get_selected_features()
        if not selected_features:
            self.dock.show_message("请先在地图上选择至少一个要素", "warning")
            return

        # 2. 检查是否都属于矢量图层
        for layer, feature in selected_features:
            if not isinstance(layer, QgsVectorLayer):
                self.dock.show_message("请确保选中的都是矢量图层要素", "warning")
                return

        # 3. 弹出编辑对话框
        dialog = NoteEditDialog(parent=self.dock)

        # 根据选中数量设置不同的提示信息
        if len(selected_features) == 1:
            layer, feature = selected_features[0]
            dialog.set_feature_info(layer.name(), feature.id())
        else:
            dialog.set_multiple_features_info(len(selected_features))

        # 4. 执行批量添加操作
        if dialog.exec_() == dialog.Accepted:
            values = dialog.get_values()
            if not values["note_text"]:
                self.dock.show_message("审查意见不能为空", "warning")
                return

            added_count = 0
            for layer, feature in selected_features:
                note = self.note_service.add_note(
                    layer=layer,
                    feature=feature,
                    text=values["note_text"],
                    priority=values["priority"],
                    author=values["author"],
                    tags=values["tags"],
                )
                if values["status"] != ReviewStatus.OPEN:
                    self.note_service.change_status(note.fid, values["status"])
                added_count += 1

            self.dock.show_message(f"已成功为 {added_count} 个要素添加批注", "success")
            self._refresh_all()

    def _on_delete_note(self, fid: int):
        """删除批注"""
        note = self.note_service.get_note_by_id(fid)
        if not note:
            return

        reply = QMessageBox.question(
            self.dock,
            "确认删除",
            f"确定要删除批注 #{fid} 吗?\n\n"
            f"图层: {note.layer_name}\n"
            f"要素: {note.feature_id}\n"
            f"意见: {note.note_text[:50]}...",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.note_service.delete_note(fid)
            self.dock.show_message(f"已删除批注 #{fid}", "success")
            self._refresh_all()

    def _on_locate_feature(self, fid: int):
        """定位要素"""
        note = self.note_service.get_note_by_id(fid)
        if not note:
            return

        # 在地图上高亮要素
        try:
            self.selection_service.highlight_feature(note.layer_id, note.feature_id)
        except Exception as e:
            log_error(f"高亮要素失败: {e}")

        # 缩放到批注位置
        self.render_service.zoom_to_note(note)
        self.dock.show_message(
            f"已定位到 {note.layer_name} 要素 {note.feature_id}", "info"
        )

    def _on_mark_resolved(self, fid: int):
        """标记完成"""
        self.note_service.change_status(fid, ReviewStatus.RESOLVED)
        self.dock.show_message(f"批注 #{fid} 已标记为完成", "success")
        self._refresh_all()

    def _on_export_report(self):
        """导出报告"""
        notes = self.note_service.get_notes_for_current_project()
        if not notes:
            self.dock.show_message("没有可导出的批注", "warning")
            return

        file_path, filter_type = QFileDialog.getSaveFileName(
            self.dock,
            "导出审查报告",
            "review_notes.csv",
            "CSV 文件 (*.csv);;GeoJSON 文件 (*.geojson)"
        )

        if not file_path:
            return

        if file_path.endswith(".csv"):
            success = self.export_service.export_to_csv(notes, file_path)
        elif file_path.endswith(".geojson"):
            success = self.export_service.export_to_geojson(notes, file_path)
        else:
            # 默认 CSV
            file_path += ".csv"
            success = self.export_service.export_to_csv(notes, file_path)

        if success:
            self.dock.show_message(f"已导出 {len(notes)} 条批注到 {os.path.basename(file_path)}", "success")
        else:
            self.dock.show_message("导出失败", "error")

    # ═══════════════════════════════════════
    #  表格交互
    # ═══════════════════════════════════════

    def _on_note_selected(self, fid: int):
        """选中批注时触发（详情面板已由 DockWidget 自行更新）"""
        pass

    def _on_note_double_clicked(self, fid: int):
        """双击行 = 定位到要素"""
        self._on_locate_feature(fid)

    # ═══════════════════════════════════════
    #  详情区操作
    # ═══════════════════════════════════════

    def _on_edit_note(self, fid: int):
        """编辑批注"""
        note = self.note_service.get_note_by_id(fid)
        if not note:
            return

        dialog = NoteEditDialog(note=note, parent=self.dock)
        if dialog.exec_() == dialog.Accepted:
            values = dialog.get_values()
            if not values["note_text"]:
                self.dock.show_message("审查意见不能为空", "warning")
                return

            updated = self.note_service.update_note(
                fid=fid,
                note_text=values["note_text"],
                priority=values["priority"],
                tags=values["tags"],
                author=values["author"],
            )

            if updated and values["status"] != note.status:
                self.note_service.change_status(fid, values["status"])

            self.dock.show_message(f"批注 #{fid} 已更新", "success")
            self._refresh_all()

    def _on_copy_note(self, fid: int):
        """复制批注内容到剪贴板"""
        note = self.note_service.get_note_by_id(fid)
        if not note:
            return

        from qgis.PyQt.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(note.note_text)
        self.dock.show_message("已复制到剪贴板", "info")

    def _on_note_history(self, fid: int):
        """查看历史（预留）"""
        self.dock.show_message("历史功能开发中...", "info")

    # ═══════════════════════════════════════
    #  筛选
    # ═══════════════════════════════════════

    def _on_filter_changed(self, filters: dict):
        """筛选条件变更"""
        notes = self.note_service.search(
            status=filters.get("status", "all"),
            priorities=filters.get("priorities", None),
            layer_name=filters.get("layer", ""),
        )
        self.dock.refresh_table(notes)
        stats = self.note_service.get_statistics()
        self.dock.update_statistics(stats)
        self.render_service.refresh_overlay(notes)

    def _on_refresh(self):
        """手动刷新"""
        self._refresh_all()
        self.dock.show_message("已刷新", "info")

    # ═══════════════════════════════════════
    #  辅助方法
    # ═══════════════════════════════════════

    def _refresh_all(self):
        """刷新表格 + 统计 + 地图标注 + 图层下拉"""
        try:
            # 更新图层下拉
            layer_names = self.note_service.get_layer_names_for_project()
            self.dock.update_layer_combo(layer_names)

            # 按当前筛选条件加载
            filters = self.dock.get_current_filters()
            notes = self.note_service.search(
                status=filters.get("status", "all"),
                priorities=filters.get("priorities", None),
                layer_name=filters.get("layer", ""),
            )
            self.dock.refresh_table(notes)

            # 更新统计
            stats = self.note_service.get_statistics()
            self.dock.update_statistics(stats)

            # 更新地图标注
            self.render_service.refresh_overlay(notes)
        except Exception as e:
            log_error(f"刷新失败: {e}")
