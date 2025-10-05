from typing import Dict

from config import setting
from config.setting import TTSServiceConfig
from schema.const import ModelType

from .base import TTSService
from .fish_speech import FishSpeechService


def get_tts_service(type: ModelType = ModelType.FISH_SPEECH) -> TTSService:
    """获取TTS服务"""
    services: Dict[ModelType, TTSServiceConfig] = {}
    for service in setting.tts_service:
        services[service.type] = service

    if type not in services:
        raise ValueError(f"不支持的TTS服务类型: {type}")

    api_url = services[type].api_url

    if type == ModelType.FISH_SPEECH:
        return FishSpeechService(api_url)
    else:
        raise ValueError(f"不支持的TTS服务类型: {type}")


__all__ = ["TTSService", "FishSpeechService", "get_tts_service"]
