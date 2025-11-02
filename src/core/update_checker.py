"""GitHub 更新检查模块"""

import re
from typing import NamedTuple

import httpx
from loguru import logger

from core.version import __version__


class VersionInfo(NamedTuple):
    """版本信息"""

    version: str
    download_url: str
    release_notes: str
    release_url: str


class UpdateChecker:
    """GitHub 更新检查器"""

    GITHUB_REPO = "MerlinCN/kinoko7danmaku"
    API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

    @staticmethod
    def get_current_version() -> str:
        """获取当前版本号

        Returns:
            当前版本号字符串
        """
        return __version__

    @staticmethod
    def parse_version(version_str: str) -> tuple[int, int, int]:
        """解析版本号字符串

        Args:
            version_str: 版本号字符串，如 "v3.0.0" 或 "3.0.0"

        Returns:
            版本号元组 (major, minor, patch)
        """
        # 移除 'v' 前缀
        version_str = version_str.lstrip("v")
        # 提取数字部分
        match = re.match(r"(\d+)\.(\d+)\.(\d+)", version_str)
        if not match:
            raise ValueError(f"无效的版本号格式: {version_str}")
        return int(match.group(1)), int(match.group(2)), int(match.group(3))

    @staticmethod
    def compare_versions(version1: str, version2: str) -> int:
        """比较两个版本号

        Args:
            version1: 版本号1
            version2: 版本号2

        Returns:
            1 表示 version1 > version2
            0 表示 version1 == version2
            -1 表示 version1 < version2
        """
        v1 = UpdateChecker.parse_version(version1)
        v2 = UpdateChecker.parse_version(version2)

        if v1 > v2:
            return 1
        if v1 < v2:
            return -1
        return 0

    @staticmethod
    def check_update() -> VersionInfo | None:
        """检查是否有新版本

        Returns:
            如果有新版本，返回 VersionInfo；否则返回 None
        """
        current_version = UpdateChecker.get_current_version()

        try:
            response = httpx.get(UpdateChecker.API_URL)
            response.raise_for_status()
            data = response.json()

            # 获取最新版本号
            latest_version = data.get("tag_name", "")
            if not latest_version:
                logger.warning("GitHub API 返回的版本号为空")
                return None

            # 比较版本号
            if UpdateChecker.compare_versions(latest_version, current_version) <= 0:
                logger.info(f"当前已是最新版本: {current_version}")
                return None

            # 查找 Windows 可执行文件的下载链接
            download_url = data.get("html_url", "")

            version_info = VersionInfo(
                version=latest_version,
                download_url=download_url,
                release_notes=data.get("body", ""),
                release_url=data.get("html_url", ""),
            )

            logger.info(f"发现新版本: {latest_version} (当前版本: {current_version})")
            return version_info

        except httpx.HTTPError as e:
            logger.exception(f"检查更新时网络错误: {e}")
            return None
        except Exception as e:
            logger.exception(f"检查更新时发生错误: {e}")
            return None
