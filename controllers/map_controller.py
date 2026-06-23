# -*- coding: utf-8 -*-
"""地图交互控制器"""

from qgis.PyQt.QtCore import QObject, Qt
from qgis.PyQt.QtWidgets import QAction
from qgis.gui import QgisInterface, QgsMapToolIdentifyFeature
from qgis.core import QgsProject, QgsVectorLayer

from ..utils.logger import log_info


class ReviewMapTool(QgsMapToolIdentifyFeature):
    """自定义地图工具：点击要素后触发回调"""

    def __init__(self, canvas, callback):
        super().__init__(canvas)
        self._callback = callback
        self.setCursor(Qt.CrossCursor)

    def canvasReleaseEvent(self, event):
        results = self.identify(event.x(), event.y())
        if results:
            for result in results:
                layer = result.mLayer
                feature = result.mFeature
                if isinstance(layer, QgsVectorLayer):
                    self._callback(layer, feature)
                    break


class MapController(QObject):
    """地图交互：识别工具、右键菜单"""

    def __init__(self, iface: QgisInterface, review_controller):
        super().__init__()
        self._iface = iface
        self._review_controller = review_controller
        self._map_tool = None
        self._context_action = None

    def enable_identify_tool(self):
        """启用识别工具"""
        canvas = self._iface.mapCanvas()
        self._map_tool = ReviewMapTool(canvas, self._on_identify)
        canvas.setMapTool(self._map_tool)
        log_info("识别工具已启用")

    def disable_identify_tool(self):
        """禁用识别工具，恢复平移"""
        if self._map_tool:
            canvas = self._iface.mapCanvas()
            canvas.unsetMapTool(self._map_tool)
            self._iface.actionPan().trigger()
            self._map_tool = None

    def _on_identify(self, layer, feature):
        """识别到要素时的回调"""
        # 选中该要素
        layer.selectByIds([feature.id()])
        # 触发添加批注流程
        self._review_controller._on_add_note()

    def add_context_menu_actions(self):
        """在图层右键菜单添加 '添加审查意见' 选项"""
        # 预留：通过 iface.layerTreeView().contextMenuAboutToShow 连接
        pass

    def cleanup(self):
        self.disable_identify_tool()
