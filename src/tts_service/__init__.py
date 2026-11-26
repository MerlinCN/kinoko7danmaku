from core.qconfig import cfg
from models.service import ServiceType

from .base import TTSService
from .edge import EdgeService
from .minimax import MinimaxService
from .omnivoice import OmniVoiceService

_default_tts_service = None


def reset_tts_service() -> None:
    """清除缓存的 TTS 服务实例

    切换使用的 TTS 服务后调用，让 get_tts_service() 重新按配置创建。
    """
    global _default_tts_service
    _default_tts_service = None


def get_tts_service() -> MinimaxService | OmniVoiceService | EdgeService:
    """获取TTS服务"""

    global _default_tts_service
    if _default_tts_service is not None:
        return _default_tts_service
    model_type = cfg.activeTTS.value
    if model_type == ServiceType.MINIMAX:
        _default_tts_service = MinimaxService()

    elif model_type == ServiceType.OMNIVOICE:
        _default_tts_service = OmniVoiceService()

    elif model_type == ServiceType.EDGE:
        _default_tts_service = EdgeService()

    else:
        raise ValueError(f'Invalid TTS service: {model_type}')
    return _default_tts_service


__all__ = [
    'EdgeService',
    'MinimaxService',
    'OmniVoiceService',
    'TTSService',
    'get_tts_service',
    'reset_tts_service',
]
