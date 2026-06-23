# -*- coding: utf-8 -*-
"""审查批注系统的枚举定义"""

from enum import Enum


class ReviewStatus(Enum):
    """批注状态"""
    OPEN = "open"                # 待处理
    IN_PROGRESS = "in_progress"  # 处理中
    RESOLVED = "resolved"        # 已完成
    WONTFIX = "wontfix"          # 不予处理


class NotePriority(Enum):
    """优先级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


# ════════════════════════════════════════════════════════
#  便捷映射表
# ════════════════════════════════════════════════════════

STATUS_DISPLAY = {
    ReviewStatus.OPEN: "待处理",
    ReviewStatus.IN_PROGRESS: "处理中",
    ReviewStatus.RESOLVED: "已完成",
    ReviewStatus.WONTFIX: "不予处理",
}

STATUS_VALUE_MAP = {
    "open": ReviewStatus.OPEN,
    "in_progress": ReviewStatus.IN_PROGRESS,
    "resolved": ReviewStatus.RESOLVED,
    "wontfix": ReviewStatus.WONTFIX,
    "pending": ReviewStatus.OPEN,  # 兼容旧数据
}

PRIORITY_DISPLAY = {
    NotePriority.LOW: "低",
    NotePriority.MEDIUM: "中",
    NotePriority.HIGH: "高",
    NotePriority.CRITICAL: "紧急",
}

PRIORITY_VALUE_MAP = {
    1: NotePriority.LOW,
    2: NotePriority.MEDIUM,
    3: NotePriority.HIGH,
    4: NotePriority.CRITICAL,
}
