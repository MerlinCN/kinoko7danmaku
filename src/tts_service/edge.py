from io import BytesIO

import edge_tts

from loguru import logger

from core.qconfig import cfg

from .base import TTSService


class EdgeService(TTSService):
    """Edge TTS 适配器"""

    def __init__(self) -> None:
        """初始化 Edge 适配器"""

    async def text_to_speech(
        self,
        text: str,
        voice: str | None = None,
        rate: str | None = None,
        volume: str | None = None,
        pitch: str | None = None,
    ) -> bytes:
        """
        使用 Edge TTS 将文本转换为语音

        Args:
            text: 要转换的文本
            voice: 使用的语音模型
            rate: 语音速率
            volume: 语音音量
            pitch: 语音音调

        Returns:
            bytes: 音频数据（MP3格式）

        Raises:
            NoAudioReceived: 如果未从服务接收到音频。
            UnexpectedResponse: 如果从服务收到意外的响应。
            UnknownResponse: 如果从服务收到未知的响应。
            WebSocketError: 如果websocket出现错误。
        """
        # 获取参数，并格式化参数为字符串
        voice = cfg.edgeVoice.value
        rate = f'{int((cfg.edgeRate.value - 1.0) * 100):+d}%'
        volume = f'{int((cfg.edgeVolume.value - 1.0) * 100):+d}%'
        pitch = f'{cfg.edgePitch.value:+d}Hz'

        # 发起请求
        audio_data = BytesIO()
        communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, volume=volume, pitch=pitch)

        async for chunk in communicate.stream():
            if chunk['type'] == 'audio':
                audio_data.write(chunk['data'])

        data = {'text': text, 'voice': voice, 'rate': rate, 'volume': volume, 'pitch': pitch}

        logger.debug(f'Edge 请求 data 为: {data}')
        logger.info(f'Edge TTS 成功: {text}')

        return audio_data.getvalue()
