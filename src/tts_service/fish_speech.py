import httpx
from loguru import logger

from config import setting

from .base import TTSService


class FishSpeechService(TTSService):
    """Fish Speech TTS适配器"""

    def __init__(self, api_url: str) -> None:
        """初始化Fish Speech适配器"""
        self.api_url = api_url

    async def text_to_speech(
        self,
        text: str,
        chunk_length: int = 200,
        seed: int = -1,
        use_memory_cache: str = "off",
        normalize: bool = True,
        streaming: bool = False,
        max_new_tokens: int = 1024,
        top_p: float = 0.8,
        repetition_penalty: float = 1.1,
        temperature: float = 0.8,
    ) -> bytes:
        """
        使用Fish Speech API将文本转换为语音

        Args:
            text: 要转换的文本
            chunk_length: 文本分块长度
            seed: 随机种子
            use_memory_cache: 是否使用内存缓存
            normalize: 是否标准化
            streaming: 是否流式输出
            max_new_tokens: 最大新token数
            top_p: top-p采样参数
            repetition_penalty: 重复惩罚
            temperature: 温度参数

        Returns:
            bytes: 音频数据（WAV格式）

        Raises:
            httpx.HTTPStatusError: HTTP请求失败
        """
        # 应用别名替换
        format_text = text
        for k, v in setting.bili_service.alias.items():
            format_text = format_text.replace(k, v)

        # 准备请求数据
        data = {
            "text": format_text,
            "chunk_length": chunk_length,
            "format": "wav",
            "seed": seed,
            "use_memory_cache": use_memory_cache,
            "normalize": normalize,
            "streaming": streaming,
            "max_new_tokens": max_new_tokens,
            "top_p": top_p,
            "repetition_penalty": repetition_penalty,
            "temperature": temperature,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.api_url, json=data, timeout=10)
            response.raise_for_status()
            logger.info(f"Fish Speech TTS 成功: {format_text}")

            return response.content
