import httpx
from loguru import logger
from tenacity import retry, retry_if_exception_type, stop_after_attempt

from core.qconfig import cfg
from models.minimax import (
    MinimaxTTSRequest,
    MinimaxTTSResponse,
    VoiceSetting,
)

from .base import TTSService


class MinimaxService(TTSService):
    """Minimax TTS适配器"""

    def __init__(self) -> None:
        """初始化Minimax适配器"""
        self.api_url = "https://api.minimax.io/v1/t2a_v2"
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=60.0,
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
        api_key: str | None = None,
        voice_id: str | None = None,
        model: str | None = None,
        speed: float | None = None,
        vol: float | None = None,
        pitch: int | None = None,
    ) -> bytes:
        """
        使用Minimax API将文本转换为语音

        Args:
            text: 要转换的文本
            api_key: API密钥，为 None 时从配置读取
            voice_id: 音色ID，为 None 时从配置读取
            model: 模型名称，为 None 时从配置读取
            speed: 语速，为 None 时从配置读取
            vol: 音量，为 None 时从配置读取
            pitch: 音调，为 None 时从配置读取

        Returns:
            bytes: 音频数据

        Raises:
            httpx.HTTPStatusError: HTTP请求失败
        """
        # 从配置中读取默认值（确保每次调用都使用最新配置）
        if api_key is None:
            api_key = cfg.minimaxApiKey.value
        if voice_id is None:
            voice_id = cfg.minimaxVoiceId.value
        if model is None:
            model = cfg.minimaxModel.value
        if speed is None:
            speed = cfg.minimaxSpeed.value
        if vol is None:
            vol = cfg.minimaxVol.value
        if pitch is None:
            pitch = cfg.minimaxPitch.value

        alias_texts = []
        if cfg.aliasDict.value:
            for k, v in cfg.aliasDict.value.items():
                alias_texts.append(f"{k}/{v}")

        request = MinimaxTTSRequest(
            model=model,
            text=text,
            voice_setting=VoiceSetting(
                voice_id=voice_id,
                speed=speed,
                vol=vol,
                pitch=pitch,
            ),
            pronunciation_dict={"tone": alias_texts},
        )
        headers = {
            "Authorization": f"Bearer {api_key}",
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
