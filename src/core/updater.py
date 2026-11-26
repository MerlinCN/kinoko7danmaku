"""自动更新模块

下载新版可执行文件，退出应用后由 PowerShell 脚本完成替换并重启。
"""

import asyncio
import hashlib
import os
import subprocess
import sys
import tempfile

from collections.abc import Callable
from pathlib import Path

import httpx

from loguru import logger

from core.const import DATA_DIR
from core.update_checker import ASSET_NAME

_UPDATE_SCRIPT_NAME = 'kinoko7danmaku-update.ps1'

_UPDATE_SCRIPT = """\
$ErrorActionPreference = 'SilentlyContinue'
while (Get-Process -Id $env:K7D_PID) { Start-Sleep -Milliseconds 300 }

for ($i = 0; $i -lt 60; $i++) {
    try {
        Move-Item -LiteralPath $env:K7D_NEW -Destination $env:K7D_TARGET -Force -ErrorAction Stop
        break
    } catch {
        Start-Sleep -Milliseconds 300
    }
}

Start-Process -FilePath $env:K7D_TARGET -WorkingDirectory (Split-Path -Path $env:K7D_TARGET)
Remove-Item -LiteralPath $MyInvocation.MyCommand.Path -Force
"""


def is_supported() -> bool:
    """当前环境是否支持自动更新

    Returns:
        仅在 Windows 下以打包形式运行时返回 True
    """
    return sys.platform == 'win32' and bool(getattr(sys, 'frozen', False))


def executable_path() -> Path:
    """当前运行的可执行文件路径

    Returns:
        可执行文件路径
    """
    return Path(sys.executable)


def can_write_install_dir() -> bool:
    """检查应用所在目录是否可写

    Returns:
        可以写入时返回 True
    """
    try:
        with tempfile.NamedTemporaryFile(dir=executable_path().parent):
            pass
    except OSError:
        return False
    return True


def _download_file(url: str, target: Path, on_progress: Callable[[int], None]) -> str:
    """下载文件并计算 sha256 摘要

    Args:
        url: 下载地址
        target: 保存路径
        on_progress: 下载进度回调，参数为 0-100 的百分比

    Returns:
        下载内容的 sha256 摘要
    """
    digest = hashlib.sha256()
    with httpx.stream('GET', url, follow_redirects=True, timeout=30.0) as response:
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        with target.open('wb') as f:
            for chunk in response.iter_bytes(1024 * 256):
                f.write(chunk)
                digest.update(chunk)
                downloaded += len(chunk)
                if total_size:
                    on_progress(downloaded * 100 // total_size)
    return digest.hexdigest()


async def download_update(
    asset_url: str,
    checksum_url: str,
    on_progress: Callable[[int], None],
) -> Path:
    """下载新版可执行文件并校验

    Args:
        asset_url: 新版 exe 的下载地址
        checksum_url: sha256 校验文件地址
        on_progress: 下载进度回调，参数为 0-100 的百分比

    Returns:
        下载完成的新 exe 路径

    Raises:
        ValueError: 校验文件无效或校验失败
        httpx.HTTPError: 下载过程中网络错误
    """
    update_dir = DATA_DIR / 'updates'
    update_dir.mkdir(parents=True, exist_ok=True)
    part_path = update_dir / f'{ASSET_NAME}.part'
    final_path = update_dir / ASSET_NAME

    loop = asyncio.get_running_loop()

    def notify_progress(percent: int) -> None:
        loop.call_soon_threadsafe(on_progress, percent)

    actual_digest = await asyncio.to_thread(_download_file, asset_url, part_path, notify_progress)

    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        checksum_response = await client.get(checksum_url)
    checksum_response.raise_for_status()
    expected_digest = checksum_response.text.split()

    if not expected_digest:
        part_path.unlink(missing_ok=True)
        raise ValueError('更新包校验文件无效，请稍后重试')

    if actual_digest != expected_digest[0].strip().lower():
        part_path.unlink(missing_ok=True)
        raise ValueError('更新包校验失败，请稍后重试')

    part_path.replace(final_path)
    on_progress(100)
    logger.info(f'更新包下载完成: {final_path}')
    return final_path


def apply_update(new_exe: Path) -> None:
    """退出应用后替换可执行文件并重启

    Args:
        new_exe: 已下载完成的新 exe

    Raises:
        RuntimeError: 当前环境不支持自动更新
    """
    if not is_supported():
        raise RuntimeError('当前环境不支持自动更新')

    script_path = Path(tempfile.gettempdir()) / _UPDATE_SCRIPT_NAME
    script_path.write_text(_UPDATE_SCRIPT, encoding='utf-8-sig')

    env = os.environ.copy()
    env['K7D_PID'] = str(os.getpid())
    env['K7D_NEW'] = str(new_exe)
    env['K7D_TARGET'] = str(executable_path())

    subprocess.Popen(
        ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script_path)],
        env=env,
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        close_fds=True,
    )
    logger.info(f'已启动更新脚本，退出后替换为 {new_exe}')
