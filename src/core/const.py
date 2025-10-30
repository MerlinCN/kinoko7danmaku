"""全局常量定义"""

from models.service import ServiceDetail, ServiceType

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
    "zh",
    "en",
    "ja",
    "ko",
    "yue",
    "all_zh",
    "all_ja",
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
