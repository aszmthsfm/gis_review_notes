# -*- coding: utf-8 -*-
"""地图标注渲染服务"""

from typing import List, Optional

from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry,
    QgsPointXY, QgsCoordinateReferenceSystem, QgsField, QgsFields,
    QgsWkbTypes, QgsSymbol, QgsSingleSymbolRenderer,
    QgsCategorizedSymbolRenderer, QgsRendererCategory,
    QgsLineSymbol, QgsFillSymbol, QgsMapLayer, QgsCoordinateTransform,
    # 标注引擎所需的依赖
    QgsPalLayerSettings, QgsVectorLayerSimpleLabeling,
    QgsTextFormat, QgsTextBufferSettings
)
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QVariant, Qt
from qgis.PyQt.QtGui import QColor, QFont

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
            project.addMapLayer(self._overlay_layer, True)
            log_info("已创建标注覆盖图层")

        return self._overlay_layer

    # 增加 show_labels 参数
    def refresh_overlay(self, notes: List[ReviewNote], show_labels: bool = False) -> None:
        """刷新地图标注"""
        layer = self.ensure_overlay_layer()
        if not layer or not layer.isValid():
            return

        # 清空旧要素
        provider = layer.dataProvider()
        provider.truncate()

        if not show_labels:
            self._apply_labeling(layer, False)  # 彻底关闭标签引擎和样式缓存
            layer.triggerRepaint()
            if self._iface and self._iface.mapCanvas():
                self._iface.mapCanvas().refresh()
            return

        #按要素(layer_id, feature_id)分组，处理多条注释重叠
        grouped_notes = {}
        for note in notes:
            if not note.geometry_wkt:
                continue
            # 以图层和要素ID作为聚类主键
            key = (note.layer_id, note.feature_id)
            if key not in grouped_notes:
                grouped_notes[key] = []
            grouped_notes[key].append(note)

        features = []
        for key, note_group in grouped_notes.items():
            geom = QgsGeometry.fromWkt(note_group[0].geometry_wkt)
            if geom.isEmpty():
                continue

            feat = QgsFeature(layer.fields())
            feat.setGeometry(geom)
            feat.setAttribute("fid", len(features))
            # 以第一条记录的 fid 作为代表
            feat.setAttribute("note_fid", note_group[0].fid)

            if len(note_group) == 1:
                # 只有一条注释
                feat.setAttribute("status", note_group[0].status.value)
                feat.setAttribute("priority", note_group[0].priority.value)
                feat.setAttribute("note_text", note_group[0].note_text[:50] if note_group[0].note_text else "")
            else:
                # 存在多条注释：拼接文本，优先级取最高以进行强警示
                texts = [f"• {n.note_text[:30]}" for n in note_group if n.note_text]
                feat.setAttribute("note_text", "\n".join(texts))

                # 提取最高优先级数值
                max_priority = max(n.priority.value for n in note_group)
                feat.setAttribute("priority", max_priority)
                # 状态取第一条的作为默认
                feat.setAttribute("status", note_group[0].status.value)

            features.append(feat)

        if features:
            provider.addFeatures(features)

        # 应用智能标注设置
        self._apply_labeling(layer, show_labels)

        layer.triggerRepaint()
        # 主动触发主地图画布刷新，确保标签立刻上屏
        if self._iface and self._iface.mapCanvas():
            self._iface.mapCanvas().refresh()
        log_info(f"标注图层已刷新: 聚合后共 {len(features)} 个标注点, 显示标签状态: {show_labels}")

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

    def _apply_labeling(self, layer: QgsVectorLayer, show_labels: bool) -> None:
        """配置 QGIS 的智能 PAL 标注引擎（强制渲染版）"""
        # 如果你没在顶部引入这些类，取消下面两行的注释：
        # from qgis.core import QgsPalLayerSettings, QgsVectorLayerSimpleLabeling, QgsTextFormat, QgsTextBufferSettings
        # from qgis.PyQt.QtGui import QColor, QFont

        if not show_labels:
            layer.setLabelsEnabled(False)
            layer.emitStyleChanged()
            return

        settings = QgsPalLayerSettings()

        # 【修复点 1】：强制使用表达式引擎解析字段
        settings.isExpression = True
        # coalesce 确保即使该行没有文本，也会显示"[空批注]"，帮你一眼定位是否是数据本身没文本的问题
        settings.fieldName = 'coalesce(NULLIF("note_text", \'\'), \'[空批注]\')'

        # 字体和颜色设置
        text_format = QgsTextFormat()
        text_format.setFont(QFont("Microsoft YaHei"))
        text_format.setSize(10.0)
        text_format.setColor(QColor(0, 0, 0))  # 纯黑色文字

        # 白边缓冲，防止文字融进底图
        buffer = QgsTextBufferSettings()
        buffer.setEnabled(True)
        buffer.setSize(1.0)
        buffer.setColor(QColor(255, 255, 255))
        text_format.setBuffer(buffer)

        settings.setFormat(text_format)

        # 排版：在点位周围 8 个方向寻找合适位置
        settings.placement = QgsPalLayerSettings.OrderedPositionsAroundPoint
        settings.obstacleSettings().setIsObstacle(True)  # 把点位本身当成障碍物，不要让文字压在点上

        # 【修复点 2：终极杀招】：关闭重叠隐藏机制！
        # 强制 QGIS 把所有标签画出来（就算字和字叠在一起也要画），这是排错的核心。
        settings.displayAll = True

        labeling = QgsVectorLayerSimpleLabeling(settings)
        layer.setLabeling(labeling)
        layer.setLabelsEnabled(True)

        # 触发图层样式重绘
        layer.emitStyleChanged()