from core.qconfig import cfg
from models.service import ServiceType

from .base import TTSService
from .edge import EdgeService
from .fish_speech import FishSpeechService
from .gpt_sovits import GPTSovitsService
from .minimax import MinimaxService
from .piper import PiperService

_default_tts_service = None


def get_tts_service() -> FishSpeechService | GPTSovitsService | MinimaxService | PiperService | EdgeService:
    """获取TTS服务"""

    global _default_tts_service
    if _default_tts_service is not None:
        return _default_tts_service
    model_type = cfg.activeTTS.value
    if model_type == ServiceType.FISH_SPEECH:
        _default_tts_service = FishSpeechService()

    elif model_type == ServiceType.GPT_SOVITS:
        _default_tts_service = GPTSovitsService()

    elif model_type == ServiceType.MINIMAX:
        _default_tts_service = MinimaxService()

    elif model_type == ServiceType.PIPER:
        _default_tts_service = PiperService()

    elif model_type == ServiceType.EDGE:
        _default_tts_service = EdgeService()

    else:
        raise ValueError(f'Invalid TTS service: {model_type}')
    return _default_tts_service


__all__ = [
    'EdgeService',
    'FishSpeechService',
    'GPTSovitsService',
    'MinimaxService',
    'PiperService',
    'TTSService',
    'get_tts_service',
]
