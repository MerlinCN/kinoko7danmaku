import httpx
from loguru import logger
from tenacity import retry, retry_if_exception_type, stop_after_attempt

from core.qconfig import cfg
from models.minimax import (
    AudioSetting,
    FilePurpose,
    FileUploadResponse,
    MinimaxTTSRequest,
    MinimaxTTSResponse,
    VoiceCloneRequest,
    VoiceCloneResponse,
    VoiceListResponse,
    VoiceSetting,
)

from .base import TTSService
from pathlib import Path


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
        if not api_key:
            raise ValueError("API Key is required")
        api_key = api_key.strip()  # 防呆设计，真的有人会加上空格或者回车
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
            audio_setting=AudioSetting(
                format="wav",  # 使用 WAV 格式，避免需要 ffmpeg 解码
                sample_rate=32000,
                bitrate=128000,
                channel=1,
            ),
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

    async def get_voice_list(self, api_key: str | None = None) -> VoiceListResponse:
        """获取音色列表

        Args:
            api_key: API密钥，为 None 时从配置读取

        Returns:
            VoiceListResponse: 音色列表响应

        Raises:
            ValueError: API Key 为空
            httpx.HTTPStatusError: HTTP请求失败
        """
        if api_key is None:
            api_key = cfg.minimaxApiKey.value
        if not api_key:
            raise ValueError("MiniMax API Key 未配置")

        api_key = api_key.strip()
        api_url = "https://api.minimax.io/v1/get_voice"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        request_body = {"voice_type": "voice_cloning"}

        client = self._get_client()
        response = await client.post(api_url, json=request_body, headers=headers)
        response.raise_for_status()

        return VoiceListResponse.model_validate(response.json())

    async def upload_audio_file(
        self,
        file_path: str,
        purpose: FilePurpose = FilePurpose.VOICE_CLONE,
        api_key: str | None = None,
    ) -> FileUploadResponse:
        """上传音频文件到 MiniMax

        Args:
            file_path: 音频文件路径
            purpose: 文件用途；voice_clone 接口源音频用 VOICE_CLONE，示例音频用 PROMPT_AUDIO
            api_key: API密钥，为 None 时从配置读取

        Returns:
            FileUploadResponse: 包含 file_id 的响应

        Raises:
            ValueError: API Key 为空或文件不存在
            httpx.HTTPStatusError: HTTP请求失败
        """
        if api_key is None:
            api_key = cfg.minimaxApiKey.value
        if not api_key:
            raise ValueError("MiniMax API Key 未配置")

        api_key = api_key.strip()
        api_url = "https://api.minimax.io/v1/files/upload"

        headers = {
            "Authorization": f"Bearer {api_key}",
        }

        # 验证文件存在

        file = Path(file_path)
        if not file.exists():
            raise ValueError(f"文件不存在: {file_path}")

        # 使用 multipart/form-data 上传文件：文件用 files，普通字段用 data
        with file.open("rb") as f:
            files = {"file": (file.name, f, "audio/*")}
            data = {"purpose": purpose.value}
            client = self._get_client()
            response = await client.post(
                api_url, files=files, data=data, headers=headers
            )
        result = response.json()
        status_msg = result.get("base_resp", {}).get("status_msg", "success")
        status_code = result.get("base_resp", {}).get("status_code", 0)
        if status_code != 0:
            raise ValueError(status_msg)

        return FileUploadResponse.model_validate(result)

    async def create_voice_clone(
        self, request: VoiceCloneRequest, api_key: str | None = None
    ) -> VoiceCloneResponse:
        """创建音色克隆

        Args:
            request: 音色克隆请求
            api_key: API密钥，为 None 时从配置读取

        Returns:
            VoiceCloneResponse: 克隆响应

        Raises:
            ValueError: API Key 为空
            httpx.HTTPStatusError: HTTP请求失败
        """
        if api_key is None:
            api_key = cfg.minimaxApiKey.value
        if not api_key:
            raise ValueError("MiniMax API Key 未配置")

        api_key = api_key.strip()
        api_url = "https://api.minimax.io/v1/voice_clone"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        client = self._get_client()
        response = await client.post(
            api_url, json=request.model_dump(exclude_none=True), headers=headers
        )
        result = response.json()
        status_code = result.get("base_resp", {}).get("status_code", 0)
        status_msg = result.get("base_resp", {}).get("status_msg", "unknown error")
        if status_code != 0:
            raise ValueError(status_msg)

        return VoiceCloneResponse.model_validate(result)

    async def delete_voice_clone(
        self, voice_id: str, api_key: str | None = None
    ) -> bool:
        """删除音色克隆

        Args:
            voice_id: 音色ID
            api_key: API密钥，为 None 时从配置读取

        Returns:
            bool: 是否删除成功

        Raises:
            ValueError: API Key 为空
            httpx.HTTPStatusError: HTTP请求失败
        """
        if api_key is None:
            api_key = cfg.minimaxApiKey.value
        if not api_key:
            raise ValueError("MiniMax API Key 未配置")

        api_key = api_key.strip()
        api_url = f"https://api.minimax.io/v1/voice_clone/{voice_id}"

        headers = {
            "Authorization": f"Bearer {api_key}",
        }

        client = self._get_client()
        response = await client.delete(api_url, headers=headers)
        response.raise_for_status()

        return True
