import httpx
from loguru import logger

from core.qconfig import cfg

from .base import TTSService


class PiperService(TTSService):
    """Piper TTS 适配器"""

    def __init__(self) -> None:
        """初始化 Piper 适配器"""
        self.api_url = cfg.piperApiUrl.value

    async def text_to_speech(
        self,
        text: str,
        voice: str | None = None,
        speaker: str | None = None,
        speaker_id: int | None = None,
        length_scale: float | None = None,
        noise_scale: float | None = None,
        noise_w_scale: float | None = None,
    ) -> bytes:
        """
        使用piper-tts API将文本转换为语音

        Args:
            text: 要转换的文本
            voice: 使用的语音模型
            speaker: 多说话人语音模型的说话人名称
            speaker_id: 多说话人语音的说话人ID, 会覆盖 speaker 参数
            length_scale: 语速
            noise_scale: 模型语音变化程度
            noise_w_scale: 模型音素时长变化程度

        Returns:
            bytes: 音频数据（WAV格式）

        Raises:
            httpx.HTTPStatusError: HTTP请求失败
        """
        if voice is None:
            voice = cfg.piperVoice.value
        if speaker is None:
            speaker = cfg.piperSpeaker.value
        if speaker_id is None:
            speaker_id = cfg.piperSpeakerId.value
        if length_scale is None:
            length_scale = cfg.piperLengthScale.value
        if noise_scale is None:
            noise_scale = cfg.piperNoiseScale.value
        if noise_w_scale is None:
            noise_w_scale = cfg.piperNoiseWScale.value

        # 准备请求数据, 过滤值为 None 或为空 的参数
        data = {
            k: v for k, v in {
                "text": text,
                "voice": voice,
                "speaker": speaker,
                "speaker_id": speaker_id,
                "length_scale": length_scale,
                "noise_scale": noise_scale,
                "noise_w_scale": noise_w_scale
            }.items() if v 
        }

        async with httpx.AsyncClient() as client:
            logger.debug(f"Piper 请求 data 为: {data}")
            response = await client.post(self.api_url, json=data, timeout=300)
            response.raise_for_status()
            logger.info(f"Piper TTS 成功: {text}")

        return response.content
