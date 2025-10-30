from config import setting
from schema.const import ServiceType

from .base import TTSService
from .fish_speech import FishSpeechService
from .gpt_sovits import GPTSovitsService
from .minimax import MinimaxService

_default_tts_service = None


def get_tts_service() -> FishSpeechService | GPTSovitsService | MinimaxService:
    """获取TTS服务"""

    global _default_tts_service
    if _default_tts_service is not None:
        return _default_tts_service
    for model_type in setting.tts_service.active:
        if model_type == ServiceType.FISH_SPEECH:
            _default_tts_service = FishSpeechService(
                setting.tts_service.fish_speech.api_url
            )
            break
        elif model_type == ServiceType.GPT_SOVITS:
            _default_tts_service = GPTSovitsService(
                setting.tts_service.gpt_sovits.api_url
            )
            break
        elif model_type == ServiceType.MINIMAX:
            _default_tts_service = MinimaxService(
                setting.tts_service.minimax.api_url,
                setting.tts_service.minimax.api_key,
                setting.tts_service.minimax.voice_id,
                setting.tts_service.minimax.model,
            )
            break
    if _default_tts_service is None:
        raise ValueError("No TTS service is active")
    return _default_tts_service


__all__ = [
    "TTSService",
    "FishSpeechService",
    "GPTSovitsService",
    "MinimaxService",
    "get_tts_service",
]
