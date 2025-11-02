"""版本信息管理"""

import sys
from pathlib import Path

from loguru import logger


def get_version() -> str:
    """获取当前应用版本号

    打包环境：从 resource/version.txt 读取
    开发环境：返回 "dev"（不需要版本号）

    Returns:
        版本号字符串，如 "3.0.0" 或 "dev"
    """
    try:
        if is_packaged():
            # 打包后的环境
            base_path = Path(sys._MEIPASS)  # type: ignore
        else:
            base_path = Path.cwd()
        version_file = base_path / "resource" / "version.txt"

        if version_file.exists():
            version = version_file.read_text(encoding="utf-8").strip()
            logger.info(f"当前版本: {version}")
            return version
        else:
            logger.warning(f"打包环境中找不到 version.txt: {version_file}")

    except Exception as e:
        logger.exception(f"读取版本号失败: {e}")
        return "unknown"


def is_packaged() -> bool:
    """判断是否为打包后的环境

    Returns:
        True 表示打包环境，False 表示开发环境
    """
    return getattr(sys, "frozen", False)


# 导出版本号
__version__ = get_version()
