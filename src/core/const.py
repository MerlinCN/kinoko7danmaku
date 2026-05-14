"""全局常量定义"""

import shutil
import sys
from pathlib import Path

from models.service import ServiceDetail, ServiceType


def get_resource_dir() -> Path:
    """获取资源目录

    打包环境：从 sys._MEIPASS 下的 resource 读取
    开发环境：从项目根目录的 resource/ 读取

    Returns:
        资源目录路径
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "resource"  # type: ignore
    return Path(__file__).resolve().parent.parent.parent / "resource"


# 资源目录
RESOURCE_DIR = get_resource_dir()


def get_data_dir() -> Path:
    """获取数据存储目录

    优先使用用户目录下的 ~/.kinoko7danmaku/，
    如果根目录存在旧的 data/ 文件夹，则自动迁移数据。

    Returns:
        数据目录路径
    """
    user_data_dir = Path.home() / ".kinoko7danmaku"
    legacy_data_dir = Path("data")

    # 如果旧目录存在且用户目录不存在，进行迁移
    if legacy_data_dir.exists() and not user_data_dir.exists():
        user_data_dir.mkdir(parents=True, exist_ok=True)
        for item in legacy_data_dir.iterdir():
            dest = user_data_dir / item.name
            if item.is_file():
                shutil.copy2(item, dest)
            elif item.is_dir():
                shutil.copytree(item, dest)

    # 确保用户数据目录存在
    user_data_dir.mkdir(parents=True, exist_ok=True)
    return user_data_dir


# 数据目录
DATA_DIR = get_data_dir()

# 支持的 TTS 服务配置
SUPPORTED_SERVICES = {
    ServiceType.MINIMAX: ServiceDetail(name=ServiceType.MINIMAX, description="MiniMax"),
    ServiceType.GPT_SOVITS: ServiceDetail(
        name=ServiceType.GPT_SOVITS, description="GPT-SoVITS"
    ),
    ServiceType.FISH_SPEECH: ServiceDetail(
        name=ServiceType.FISH_SPEECH, description="Fish Speech"
    ),
    ServiceType.PIPER: ServiceDetail(
        name=ServiceType.PIPER, description="Piper"
    ),
}

# MiniMax 支持的模型列表
MINIMAX_MODELS = [
    "speech-2.8-hd",
    "speech-2.8-turbo",
    "speech-2.6-hd",
    "speech-2.6-turbo",
    "speech-02-hd",
    "speech-02-turbo",
    "speech-01-hd",
    "speech-01-turbo",
]

# GPT-SoVITS 语言选项
GPT_SOVITS_LANGUAGES = [
    "auto",
    "Chinese",
    "English",
    "Japanese",
    "Korean",
    "Cantonese",
    "Multilingual Mixed",
]

# GPT-SoVITS 文本切分方式
GPT_SOVITS_TEXT_SPLIT_METHODS = [
    "不切",
    "凑四句一切",
    "凑50字一切",
    "按中文句号。切",
    "按英文句号.切",
    "按标点符号切",
]

MINIMAX_ERROR_VOICE_ID = "未获取到音色列表，请检查API 密钥，然后刷新"


COOKIES_PATH = DATA_DIR / "cookies.json"

GITHUB_URL = "https://github.com/MerlinCN/kinoko7danmaku"

AUTHOR_BILIBILI_URL = "https://space.bilibili.com/103049147"
