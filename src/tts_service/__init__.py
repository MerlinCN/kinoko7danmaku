from config import setting
from schema.const import ModelType

from .base import TTSService
from .fish_speech import FishSpeechService
from .gpt_sovits import GPTSovitsService

DEFAULT_TTS = ModelType.FISH_SPEECH


_fish_speech_service = FishSpeechService(setting.fish_speech.api_url)
_gpt_sovits_service = GPTSovitsService(setting.gpt_sovits.api_url)


def get_tts_service(
    type: ModelType = DEFAULT_TTS,
) -> FishSpeechService | GPTSovitsService:
    """获取TTS服务"""
    if type == ModelType.FISH_SPEECH:
        return _fish_speech_service
    elif type == ModelType.GPT_SOVITS:
        return _gpt_sovits_service


__all__ = ["TTSService", "FishSpeechService", "get_tts_service"]
