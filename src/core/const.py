"""全局常量定义"""

import shutil
from pathlib import Path

from models.service import ServiceDetail, ServiceType


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

MINIMAX_VOICE_IDS = {
    "kinoko7_v1": "kinoko7_v1",
    "moss_audio_05599258-a2c0-11f0-abb1-3ebcbb261618": "Isabel",
    "moss_audio_6d40e743-357b-11f0-b24c-2e48b7cbf811": "Merlin",
    "moss_audio_638d754a-357e-11f0-9505-4e9b7ef777f4": "芋艿",
}


COOKIES_PATH = DATA_DIR / "cookies.json"

GITHUB_URL = "https://github.com/MerlinCN/kinoko7danmaku"

AUTHOR_BILIBILI_URL = "https://space.bilibili.com/103049147"
