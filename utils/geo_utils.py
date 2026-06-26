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
    geom = feature.geometry()
    if geom is None or geom.isEmpty():
        return ""

    # 修改点：确保点必定落在面上/线上
    target_point = geom.pointOnSurface()
    if target_point is None or target_point.isEmpty():
        return ""

    target_crs = QgsCoordinateReferenceSystem("EPSG:4326")
    if layer_crs and layer_crs != target_crs:
        transform = QgsCoordinateTransform(
            layer_crs, target_crs, QgsProject.instance()
        )
        target_point.transform(transform)

    point = target_point.asPoint()
    return f"POINT({point.x()} {point.y()})"