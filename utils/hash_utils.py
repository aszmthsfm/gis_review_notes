# -*- coding: utf-8 -*-
"""项目哈希计算工具"""

import hashlib
import os


def compute_project_hash(project_path: str) -> str:
    """基于 QGS/QGZ 绝对路径 + 文件修改时间生成 SHA256

    :param project_path: QGIS 项目文件路径 (.qgs / .qgz)
    :return: 64 字符的十六进制哈希字符串
    """
    if not project_path:
        return "unsaved_project"

    try:
        abspath = os.path.abspath(project_path)
        stat = os.stat(abspath)
        raw = f"{abspath}|{stat.st_mtime_ns}"
        return hashlib.sha256(raw.encode()).hexdigest()
    except (OSError, IOError):
        # 文件不存在或无法访问时，仅用路径做哈希
        return hashlib.sha256(project_path.encode()).hexdigest()
