# -*- coding: utf-8 -*-
"""地图标注渲染服务"""

from typing import List, Optional

from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry,
    QgsPointXY, QgsCoordinateReferenceSystem, QgsField, QgsFields,
    QgsWkbTypes, QgsSymbol, QgsSingleSymbolRenderer,
    QgsCategorizedSymbolRenderer, QgsRendererCategory,
    QgsLineSymbol, QgsFillSymbol, QgsTextFormat,
    QgsMapLayer, QgsCoordinateTransform
)
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QVariant, Qt
from qgis.PyQt.QtGui import QColor

from ..core.constants import Constants
from ..core.models import ReviewNote
from ..core.enums import ReviewStatus
from ..utils.logger import log_info, log_error


class RenderService:
    """在地图上渲染审查标注（内存图层）"""

    def __init__(self, iface: QgisInterface):
        self._iface = iface
        self._overlay_layer: Optional[QgsVectorLayer] = None

    def ensure_overlay_layer(self) -> QgsVectorLayer:
        """创建或获取内存标注图层"""
        project = QgsProject.instance()

        # 检查是否已存在
        for layer in project.mapLayers().values():
            if layer.name() == Constants.OVERLAY_LAYER_NAME:
                self._overlay_layer = layer
                return layer

        # 创建新的内存图层
        uri = "Point?crs=EPSG:4326&field=fid:integer&field=note_fid:integer&field=status:string&field=priority:integer&field=note_text:string"

        # ⚠️ 修复: 原代码缺失了下面这行实例化代码，会导致图层创建失败并引发无法添加注释的连锁报错
        self._overlay_layer = QgsVectorLayer(uri, Constants.OVERLAY_LAYER_NAME, "memory")

        if self._overlay_layer.isValid():
            # 设置图层为私有，并且免除内存图层保存提示
            self._overlay_layer.setFlags(QgsMapLayer.Private | QgsMapLayer.Identifiable)
            self._overlay_layer.setCustomProperty("skipMemorySave", 1)

            # 设置样式
            self._apply_symbology(self._overlay_layer)

            # 添加到项目（插入到最底层，不干扰数据图层）
            project.addMapLayer(self._overlay_layer, False)
            log_info("已创建标注覆盖图层")

        return self._overlay_layer

    def refresh_overlay(self, notes: List[ReviewNote]) -> None:
        """刷新地图标注"""
        layer = self.ensure_overlay_layer()
        if not layer or not layer.isValid():
            return

        # 清空旧要素
        provider = layer.dataProvider()
        provider.truncate()

        # 添加新要素
        features = []
        for note in notes:
            if not note.geometry_wkt:
                continue
            geom = QgsGeometry.fromWkt(note.geometry_wkt)
            if geom.isEmpty():
                continue

            feat = QgsFeature(layer.fields())
            feat.setGeometry(geom)
            feat.setAttribute("fid", len(features))
            feat.setAttribute("note_fid", note.fid)
            feat.setAttribute("status", note.status.value)
            feat.setAttribute("priority", note.priority.value)
            feat.setAttribute("note_text", note.note_text[:50] if note.note_text else "")
            features.append(feat)

        if features:
            provider.addFeatures(features)

        layer.triggerRepaint()
        log_info(f"标注图层已刷新: {len(features)} 个标注")

    def clear_overlay(self) -> None:
        """清除标注图层"""
        project = QgsProject.instance()
        if self._overlay_layer:
            project.removeMapLayer(self._overlay_layer.id())
            self._overlay_layer = None

    def cleanup(self) -> None:
        """在 QGIS 关闭或卸载插件时被调用，确保内存图层被销毁"""
        self.clear_overlay()

    def zoom_to_note(self, note: ReviewNote) -> None:
        """缩放到指定批注的位置"""
        if not note.geometry_wkt:
            return

        geom = QgsGeometry.fromWkt(note.geometry_wkt)
        if geom.isEmpty():
            return

        canvas = self._iface.mapCanvas()

        # 1. 坐标系转换：数据库固定为 EPSG:4326，需转为当前画布的坐标系
        crs_src = QgsCoordinateReferenceSystem("EPSG:4326")
        crs_dest = canvas.mapSettings().destinationCrs()

        if crs_src != crs_dest:
            transform = QgsCoordinateTransform(crs_src, crs_dest, QgsProject.instance())
            geom.transform(transform)

        # 2. 定位到点：因为点要素 BoundingBox 宽高为 0，不能用 setExtent
        center_point = geom.asPoint()
        canvas.setCenter(center_point)

        # 3. 优化缩放体验
        if canvas.scale() > 5000:
            canvas.zoomScale(5000)

        canvas.refresh()

    def _apply_symbology(self, layer: QgsVectorLayer) -> None:
        """应用分类符号化：按状态分色"""
        categories = []

        status_configs = [
            (ReviewStatus.OPEN.value, QColor(230, 57, 70), "待处理"),
            (ReviewStatus.IN_PROGRESS.value, QColor(255, 165, 0), "处理中"),
            (ReviewStatus.RESOLVED.value, QColor(0, 153, 76), "已完成"),
            (ReviewStatus.WONTFIX.value, QColor(128, 128, 128), "不予处理"),
        ]

        for status_val, color, label in status_configs:
            symbol = QgsSymbol.defaultSymbol(QgsWkbTypes.PointGeometry)
            symbol.setColor(color)
            symbol.setSize(6)
            categories.append(QgsRendererCategory(status_val, symbol, label))

        renderer = QgsCategorizedSymbolRenderer("status", categories)
        layer.setRenderer(renderer)