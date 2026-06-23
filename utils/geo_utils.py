# -*- coding: utf-8 -*-
"""地理工具函数"""

from qgis.core import (
    QgsGeometry,
    QgsFeature,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
)


def feature_to_centroid_wkt(
    feature: QgsFeature,
    layer_crs: QgsCoordinateReferenceSystem = None,
) -> str:
    """获取要素的质心 WKT 字符串 (EPSG:4326)

    用于在地图标注图层上绘制批注点位。

    :param feature: 要素对象
    :param layer_crs: 要素所属图层的 CRS，若为 None 则不转换
    :return: WKT 字符串，如 "POINT(114.35 30.59)"；无几何则返回空字符串
    """
    geom = feature.geometry()
    if geom is None or geom.isEmpty():
        return ""

    centroid = geom.centroid()
    if centroid is None or centroid.isEmpty():
        return ""

    # 坐标转换到 EPSG:4326
    target_crs = QgsCoordinateReferenceSystem("EPSG:4326")
    if layer_crs and layer_crs != target_crs:
        transform = QgsCoordinateTransform(
            layer_crs, target_crs, QgsProject.instance()
        )
        centroid.transform(transform)

    point = centroid.asPoint()
    return f"POINT({point.x()} {point.y()})"
