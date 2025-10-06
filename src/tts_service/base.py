from abc import ABC, abstractmethod
from typing import Any


class TTSService(ABC):
    """TTS适配器基类，定义统一的接口规范"""

    def __init__(self, api_url: str):
        self.api_url = api_url

    @abstractmethod
    async def text_to_speech(self, text: str, **kwargs: Any) -> bytes:
        """
        将文本转换为语音

        Args:
            text: 要转换的文本
            **kwargs: 其他参数，由具体适配器实现定义

        Returns:
            bytes: 音频数据（WAV格式）
        """
        pass
