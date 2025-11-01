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
