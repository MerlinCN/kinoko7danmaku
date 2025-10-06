import time
from typing import Any, Dict, List, Optional

import aiohttp
import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt

from config import setting

from .base import TTSService


class GradioClient:
    """
    Minimal Gradio client to talk to GPT-SoVITS WebUI following the behavior
    referenced in gpt-sovits-tts/tts.py and tts_client.py.
    """

    def __init__(self, base_url: str, ssl_verify: bool = False, timeout: int = 300):
        self.base_url = base_url if base_url.endswith("/") else (base_url + "/")
        self.ssl_verify = ssl_verify
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None
        self._fn_map: Dict[str, int] = {}

    async def ensure(self):
        if self._session is None:
            connector = aiohttp.TCPConnector(ssl=self.ssl_verify)
            self._session = aiohttp.ClientSession(
                timeout=self.timeout, connector=connector
            )
            await self._load_config()

    async def _load_config(self):
        assert self._session is not None
        url = self.base_url + "config"
        async with self._session.get(url) as resp:
            resp.raise_for_status()
            cfg = await resp.json()
        deps = cfg.get("dependencies") or []
        # Build api_name -> fn_index map
        for i, dep in enumerate(deps):
            api_name = (dep or {}).get("api_name")
            if api_name:
                self._fn_map[str(api_name).strip().lstrip("/")] = int(
                    (dep or {}).get("id", i)
                )

    async def close(self):
        if self._session is not None:
            s = self._session
            self._session = None
            try:
                await s.close()
            except Exception:
                pass

    async def _upload_file(self, file_path: str) -> str:
        assert self._session is not None
        url = self.base_url + "upload"
        data = aiohttp.FormData()
        with open(file_path, "rb") as f:
            file_content = f.read()
        data.add_field(
            "files",
            file_content,
            filename=file_path.split("/")[-1],
            content_type="application/octet-stream",
        )
        async with self._session.post(url, data=data) as resp:
            resp.raise_for_status()
            j = await resp.json()
            # returns list of uploaded paths
            return j[0]

    async def _process_inputs(self, args: List[Any]) -> List[Any]:
        processed: List[Any] = []
        for a in args:
            if (
                isinstance(a, dict)
                and a.get("meta", {}).get("_type") == "gradio.FileData"
            ):
                p = a.get("path")
                if p and not (
                    str(p).startswith("http://") or str(p).startswith("https://")
                ):
                    # local path -> upload
                    uploaded = await self._upload_file(p)
                    processed.append(
                        {
                            "path": uploaded,
                            "orig_name": a.get("orig_name") or (str(p).split("/")[-1]),
                            "meta": {"_type": "gradio.FileData"},
                        }
                    )
                else:
                    processed.append(a)
            else:
                processed.append(a)
        return processed

    async def predict(self, api_name: str, *args: Any) -> Any:
        await self.ensure()
        assert self._session is not None
        fn = self._fn_map.get(api_name.strip().lstrip("/"))
        if fn is None:
            raise RuntimeError(f"API '{api_name}' not found in gradio config")
        url = self.base_url + "api/predict/"
        data = {
            "data": await self._process_inputs(list(args)),
            "fn_index": fn,
            "session_hash": str(int(time.time() * 1000)),
        }
        async with self._session.post(url, json=data, timeout=30) as resp:
            text = await resp.text()
            if resp.status != 200:
                raise RuntimeError(f"Gradio predict failed: {resp.status} {text[:200]}")
            j = await resp.json()
            if j.get("error"):
                raise RuntimeError(f"Gradio API error: {j.get('error')}")
            return j.get("data")


class GPTSovitsService(TTSService):
    """GPTSovits TTS适配器"""

    def __init__(self, api_url: str):
        self.client = GradioClient(api_url)

    async def close(self):
        await self.client.close()

    async def init(self):
        await self.client.ensure()
        result = await self.client.predict(
            "/change_sovits_weights",
            setting.tts_service.gpt_sovits.sovits_model,
            setting.tts_service.gpt_sovits.text_lang,
            setting.tts_service.gpt_sovits.text_lang,
        )
        logger.info(f"Changed SoVITS weights: {result}")
        result = await self.client.predict(
            "/change_gpt_weights", setting.tts_service.gpt_sovits.gpt_model
        )
        logger.info(f"Changed GPT weights: {result}")

    @retry(stop=stop_after_attempt(3))
    async def text_to_speech(
        self,
        text: str,
        text_lang: str = setting.tts_service.gpt_sovits.text_lang,
        ref_audio_path: str = setting.tts_service.gpt_sovits.ref_audio_path,
        ref_text: str = setting.tts_service.gpt_sovits.ref_text,
        ref_text_lang: str = setting.tts_service.gpt_sovits.ref_text_lang,
        top_k: int = setting.tts_service.gpt_sovits.top_k,
        top_p: float = setting.tts_service.gpt_sovits.top_p,
        temperature: float = setting.tts_service.gpt_sovits.temperature,
        text_split_method: str = setting.tts_service.gpt_sovits.text_split_method,
        speed_factor: float = setting.tts_service.gpt_sovits.speed_factor,
        ref_text_free: bool = setting.tts_service.gpt_sovits.ref_text_free,
        sample_steps: int = setting.tts_service.gpt_sovits.sample_steps,
        super_sampling: bool = setting.tts_service.gpt_sovits.super_sampling,
        pause_seconds: float = setting.tts_service.gpt_sovits.pause_seconds,
    ) -> bytes:
        """
        使用GPTSovits API将文本转换为语音

        Args:
            text: 要转换的文本
            text_lang: 文本语言
            ref_audio_path: 参考音频路径
            ref_text: 参考文本
            ref_text_lang: 参考文本语言
            top_k: Top K采样参数
            top_p: Top P采样参数
            temperature: 采样温度
            text_split_method: 文本切分方式
            speed_factor: 语速调整
            ref_text_free: 无参考文本模式
            sample_steps: 采样步数
            super_sampling: 超采样
            pause_seconds: 句间停顿秒数

        Returns:
            bytes: 音频数据（WAV格式）
        """
        ref_audio_dict = {
            "path": ref_audio_path,
            "orig_name": ref_audio_path.split("/")[-1],
            "meta": {"_type": "gradio.FileData"},
        }
        is_freeze = False  # 是否冻结模型
        inp_refs = None  # 输入的参考音频
        data = await self.client.predict(
            "/get_tts_wav",
            ref_audio_dict,
            ref_text,
            ref_text_lang,
            text,
            text_lang,
            text_split_method,
            top_k,
            top_p,
            temperature,
            ref_text_free,
            speed_factor,
            is_freeze,
            inp_refs,
            sample_steps,
            super_sampling,
            pause_seconds,
        )

        # 读取返回的音频文件
        audio_path = data[0].get("url")
        async with httpx.AsyncClient() as client:
            response = await client.get(audio_path)
            response.raise_for_status()
            return response.content
