"""GitHub 更新检查模块"""

import json
import re
import time
from pathlib import Path
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
    CACHE_FILE = Path("data/update_cache.json")
    CHECK_INTERVAL = 3600 * 1  # 1 小时检查一次

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
    def _load_cache() -> dict:
        """加载缓存数据

        Returns:
            缓存字典，包含 etag、last_check_time 和 latest_version
        """
        if not UpdateChecker.CACHE_FILE.exists():
            return {}

        try:
            with open(UpdateChecker.CACHE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"读取更新缓存失败: {e}")
            return {}

    @staticmethod
    def _save_cache(
        etag: str | None,
        last_check_time: float,
        latest_version: str | None = None,
        release_info: dict | None = None,
    ) -> None:
        """保存缓存数据

        Args:
            etag: ETag 值
            last_check_time: 上次检查时间戳
            latest_version: 上次检测到的最新版本号
            release_info: 发布信息（download_url、release_notes、release_url）
        """
        try:
            UpdateChecker.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            cache_data = {
                "etag": etag,
                "last_check_time": last_check_time,
                "latest_version": latest_version,
                "release_info": release_info,
            }
            with open(UpdateChecker.CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"保存更新缓存失败: {e}")

    @staticmethod
    def _check_version_from_cache(
        current_version: str,
        cached_latest_version: str | None,
        cached_release_info: dict | None,
    ) -> VersionInfo | None:
        """从缓存中检查版本更新

        Args:
            current_version: 当前版本号
            cached_latest_version: 缓存的最新版本号
            cached_release_info: 缓存的发布信息

        Returns:
            如果有新版本，返回 VersionInfo；否则返回 None
        """
        if not cached_latest_version:
            logger.info(f"当前已是最新版本: {current_version}")
            return None

        if UpdateChecker.compare_versions(cached_latest_version, current_version) > 0:
            logger.info(
                f"发现新版本: {cached_latest_version} (当前版本: {current_version})（来自缓存）"
            )
            if cached_release_info:
                return VersionInfo(
                    version=cached_latest_version,
                    download_url=cached_release_info.get("download_url", ""),
                    release_notes=cached_release_info.get("release_notes", ""),
                    release_url=cached_release_info.get("release_url", ""),
                )
        else:
            logger.info(f"当前已是最新版本: {current_version}")

        return None

    @staticmethod
    def check_update(force: bool = False) -> VersionInfo | None:
        """检查是否有新版本

        Args:
            force: 是否强制检查（忽略检查间隔）

        Returns:
            如果有新版本，返回 VersionInfo；否则返回 None
        """
        current_version = UpdateChecker.get_current_version()
        current_time = time.time()

        # 加载缓存
        cache = UpdateChecker._load_cache()
        last_check_time = cache.get("last_check_time", 0)
        etag = cache.get("etag")
        cached_latest_version = cache.get("latest_version")
        cached_release_info = cache.get("release_info")

        # 检查是否需要 API 请求（距离上次检查时间）
        should_skip_api = (
            not force
            and (current_time - last_check_time) < UpdateChecker.CHECK_INTERVAL
        )

        if should_skip_api:
            logger.info(
                f"距离上次检查不足 {UpdateChecker.CHECK_INTERVAL / 3600:.1f} 小时，跳过 API 请求"
            )
            # 即使跳过 API 请求，也要检查缓存中的版本
            return UpdateChecker._check_version_from_cache(
                current_version, cached_latest_version, cached_release_info
            )

        # 发起 API 请求
        try:
            headers = {"If-None-Match": etag} if etag else {}
            response = httpx.get(UpdateChecker.API_URL, headers=headers, timeout=10.0)

            # 403 限流：返回缓存
            if response.status_code == 403:
                logger.warning("GitHub API 限流，使用缓存数据")
                return UpdateChecker._check_version_from_cache(
                    current_version, cached_latest_version, cached_release_info
                )

            # 304 未修改：更新检查时间，返回缓存
            if response.status_code == 304:
                UpdateChecker._save_cache(
                    etag, current_time, cached_latest_version, cached_release_info
                )
                return UpdateChecker._check_version_from_cache(
                    current_version, cached_latest_version, cached_release_info
                )

            # 检查其他 HTTP 错误
            response.raise_for_status()

            # 解析新版本数据
            data = response.json()
            latest_version = data.get("tag_name", "")
            if not latest_version:
                logger.warning("GitHub API 返回的版本号为空")
                return None

            # 保存到缓存
            new_etag = response.headers.get("etag", etag)
            release_info = {
                "download_url": data.get("html_url", ""),
                "release_notes": data.get("body", ""),
                "release_url": data.get("html_url", ""),
            }
            UpdateChecker._save_cache(
                new_etag, current_time, latest_version, release_info
            )

            # 比较版本
            if UpdateChecker.compare_versions(latest_version, current_version) <= 0:
                logger.info(f"当前已是最新版本: {current_version}")
                return None

            logger.info(f"发现新版本: {latest_version} (当前版本: {current_version})")
            return VersionInfo(
                version=latest_version,
                download_url=release_info["download_url"],
                release_notes=release_info["release_notes"],
                release_url=release_info["release_url"],
            )

        except httpx.TimeoutException:
            logger.warning("检查更新超时，使用缓存数据")
            return UpdateChecker._check_version_from_cache(
                current_version, cached_latest_version, cached_release_info
            )
        except httpx.HTTPStatusError as e:
            logger.warning(
                f"检查更新时 HTTP 错误: {e.response.status_code}，使用缓存数据"
            )
            return UpdateChecker._check_version_from_cache(
                current_version, cached_latest_version, cached_release_info
            )
        except httpx.HTTPError as e:
            logger.warning(f"检查更新时网络错误: {e}，使用缓存数据")
            return UpdateChecker._check_version_from_cache(
                current_version, cached_latest_version, cached_release_info
            )
        except Exception as e:
            logger.warning(f"检查更新时发生错误: {e}，使用缓存数据")
            return UpdateChecker._check_version_from_cache(
                current_version, cached_latest_version, cached_release_info
            )
