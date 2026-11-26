"""OmniVoice 本地 TTS 适配器"""

from http import HTTPStatus

import httpx

from loguru import logger

from core.omnivoice_runtime import omnivoice_runtime
from core.omnivoice_settings import load_settings
from core.qconfig import cfg

from .base import TTSService

DEFAULT_NUM_STEP = 16


class OmniVoiceService(TTSService):
    """OmniVoice 本地 TTS 适配器

    调用本机常驻的 OmniVoice 合成服务，运行时未启动时会自动拉起。
    """

    def __init__(self) -> None:
        """初始化适配器"""
        super().__init__(f'http://127.0.0.1:{cfg.omnivoicePort.value}')

    async def text_to_speech(
        self,
        text: str,
        ref_audio: str | None = None,
        ref_text: str | None = None,
        num_step: int | None = None,
        speed: float | None = None,
    ) -> bytes:
        """将文本转换为语音

        Args:
            text: 要转换的文本
            ref_audio: 参考音频路径，为 None 时读取保存的参数
            ref_text: 参考文本，为 None 时读取保存的参数
            num_step: 扩散步数，为 None 时使用默认值
            speed: 语速，为 None 时读取保存的参数

        Returns:
            bytes: WAV 格式音频数据

        Raises:
            RuntimeError: 本地运行时未安装或启动失败
            httpx.HTTPStatusError: 合成服务返回错误
        """
        settings = load_settings()
        payload = {
            'text': text,
            'ref_audio': settings.ref_audio if ref_audio is None else ref_audio,
            'ref_text': settings.ref_text if ref_text is None else ref_text,
            'num_step': DEFAULT_NUM_STEP if num_step is None else num_step,
            'speed': settings.speed if speed is None else speed,
        }

        base_url = await omnivoice_runtime.ensure_running(
            cfg.omnivoicePort.value,
            cfg.omnivoiceHfEndpoint.value,
        )
        logger.debug(f'OmniVoice 合成请求: {payload}')
        async with httpx.AsyncClient(timeout=600.0, trust_env=False) as client:
            response = await client.post(f'{base_url}/tts', json=payload)
        if response.status_code != HTTPStatus.OK:
            raise RuntimeError(response.json()['error'])
        audio = response.content
        logger.debug(f'OmniVoice 合成完成: {len(audio)} 字节')
        return audio
