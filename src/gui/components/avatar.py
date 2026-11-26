"""头像加载工具"""

import aiohttp

from PySide6.QtGui import QPixmap
from loguru import logger


async def load_avatar_pixmap(url: str) -> QPixmap | None:
    """下载头像图片

    Args:
        url: 头像图片地址

    Returns:
        头像位图，下载或解析失败时返回 None
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.read()
    except aiohttp.ClientError as e:
        logger.warning(f'加载头像失败: {e!r}')
        return None

    pixmap = QPixmap()
    if not pixmap.loadFromData(data):
        logger.warning(f'头像解析失败: {url}')
        return None
    return pixmap
