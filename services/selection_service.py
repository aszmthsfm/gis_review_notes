# -*- coding: utf-8 -*-
"""要素选择管理服务"""

from typing import Optional, List, Tuple

from qgis.core import QgsProject, QgsMapLayer, QgsVectorLayer, QgsFeature
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import pyqtSignal, QObject


class SelectionService(QObject):
    """管理 QGIS 要素选择"""

    selection_changed = pyqtSignal()

    def __init__(self, iface: QgisInterface):
        super().__init__()
        self._iface = iface

    def get_selected_features(self) -> List[Tuple[QgsVectorLayer, QgsFeature]]:
        """获取所有图层中选中的要素列表"""
        result = []
        project = QgsProject.instance()
        for layer_id in project.mapLayers():
            layer = project.mapLayer(layer_id)
            if isinstance(layer, QgsVectorLayer):
                for feature in layer.selectedFeatures():
                    result.append((layer, feature))
        return result

    def get_single_selected_feature(self) -> Optional[Tuple[QgsVectorLayer, QgsFeature]]:
        """获取单选的一个要素（当只有一个图层选了要素时）"""
        features = self.get_selected_features()
        if len(features) == 1:
            return features[0]
        return None

    def get_active_layer_selected_features(self) -> List[QgsFeature]:
        """获取当前活动图层中选中的要素"""
        layer = self._iface.activeLayer()
        if isinstance(layer, QgsVectorLayer) and layer.selectedFeatureCount() > 0:
            return list(layer.selectedFeatures())
        return []

    def highlight_feature(self, layer_id: str, feature_id: int) -> None:
        """高亮选中指定要素"""
        project = QgsProject.instance()
        layer = project.mapLayer(layer_id)
        if isinstance(layer, QgsVectorLayer):
            layer.selectByIds([feature_id])
            self._iface.setActiveLayer(layer)

    def clear_selection(self) -> None:
        """清除所有选择"""
        project = QgsProject.instance()
        for layer in project.mapLayers().values():
            if isinstance(layer, QgsVectorLayer):
                layer.removeSelection()
