import httpx
from loguru import logger
from tenacity import retry, retry_if_exception_type, stop_after_attempt

from config import setting
from schema.minimax import (
    MinimaxTTSRequest,
    MinimaxTTSResponse,
    VoiceSetting,
)

from .base import TTSService


class MinimaxService(TTSService):
    """Minimax TTS适配器"""

    def __init__(self, api_url: str, api_key: str, voice_id: str, model: str) -> None:
        """初始化Minimax适配器"""
        self.api_url = api_url
        self.api_key = api_key
        self.voice_id = voice_id
        self.model = model
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=60.0,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )
        return self._client

    async def close(self) -> None:
        """关闭 HTTP 客户端"""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    @retry(
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(httpx.ConnectError),
        reraise=True,
    )
    async def text_to_speech(
        self,
        text: str,
        speed: float = setting.tts_service.minimax.speed,
        vol: float = setting.tts_service.minimax.vol,
        pitch: int = setting.tts_service.minimax.pitch,
    ) -> bytes:
        """
        使用Minimax API将文本转换为语音

        Args:
            text: 要转换的文本
            speed: 语速
            vol: 音量
            pitch: 音调

        Returns:
            bytes: 音频数据

        Raises:
            httpx.HTTPStatusError: HTTP请求失败
        """
        alias_texts = []
        for k, v in setting.bili_service.alias.items():
            alias_texts.append(f"{k}/{v}")

        request = MinimaxTTSRequest(
            model=self.model,
            text=text,
            voice_setting=VoiceSetting(
                voice_id=self.voice_id,
                speed=speed,
                vol=vol,
                pitch=pitch,
            ),
            pronunciation_dict={"tone": alias_texts},
        )
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        logger.debug(f"Minimax TTS 请求开始: {text[:50]}...")

        client = self._get_client()
        logger.debug(f"发送 POST 请求到: {self.api_url}")

        response = await client.post(
            self.api_url, json=request.model_dump(), headers=headers
        )
        logger.debug(f"收到响应，状态码: {response.status_code}")

        response.raise_for_status()

        result: MinimaxTTSResponse = MinimaxTTSResponse.model_validate(response.json())

        audio_bytes = bytes.fromhex(result.data.audio)
        logger.info(
            f"Minimax TTS 成功: {text[:50]}... (音频大小: {len(audio_bytes)} 字节)"
        )

        return audio_bytes
