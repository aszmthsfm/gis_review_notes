# -*- coding: utf-8 -*-
"""统一日志工具，封装 QgsMessageLog"""

from qgis.core import QgsMessageLog, Qgis

TAG = "GIS Review Notes"


def log_info(message: str):
    """输出 Info 级别日志"""
    QgsMessageLog.logMessage(message, TAG, Qgis.Info)


def log_warning(message: str):
    """输出 Warning 级别日志"""
    QgsMessageLog.logMessage(message, TAG, Qgis.Warning)


def log_error(message: str):
    """输出 Critical 级别日志"""
    QgsMessageLog.logMessage(message, TAG, Qgis.Critical)
