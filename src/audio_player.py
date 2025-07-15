import io

import httpx
import pyaudio
import sounddevice as sd
from loguru import logger
from pydub import AudioSegment

from config import config_manager


class StreamPlayer:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.device_index = sd.default.device[1]

    def get_output_devices(self):
        """获取设备选择列表（使用sounddevice）- 返回元组列表格式供Gradio使用"""

        # 获取所有设备
        all_devices: list[dict] = sd.query_devices()  # type: ignore
        default_output_index: int = sd.default.device[1]  # type: ignore

        default_output_device: dict = all_devices[default_output_index]  # type: ignore

        choices = [("默认设备", default_output_index)]

        default_api: str = sd.query_hostapis()[default_output_device["hostapi"]]["name"]  # type: ignore
        # 遍历所有设备，只添加纯输出设备
        for idx, device in enumerate(all_devices):
            if device["max_output_channels"] > 0:  # 只要纯输出设备
                # 构建设备名称
                name = device["name"]
                # 标记默认设备
                if idx == default_output_index:
                    name += " (默认) "

                # 标记推荐的WASAPI接口（通用，不针对特定品牌）
                api_name: str = sd.query_hostapis()[device["hostapi"]]["name"]  # type: ignore
                if default_api not in api_name:
                    continue
                choices.append((name, idx))  # (显示名称, 实际索引)

        logger.info(f"检测到 {len(choices) - 1} 个纯输出设备")
        return choices

    def set_output_device(self, device_index: int):
        """设置输出设备"""
        try:
            if device_index == -1:
                device_index = sd.default.device[1]  # type: ignore
            device_info: dict = sd.query_devices(device_index)  # type: ignore
            if int(device_info["max_output_channels"]) > 0:  # type: ignore
                logger.info(f"已设置输出设备: {device_info['name']}")
                self.device_index = device_index
                return True
            else:
                logger.error(f"设备 {device_index} 不支持音频输出")
                return False
        except Exception as e:
            logger.error(f"设置设备失败: {e}")
            return False

    def play_bytes(self, audio_bytes):
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        raw = audio.raw_data
        sw, ch, rate = audio.sample_width, audio.channels, audio.frame_rate

        stream = self.p.open(
            format=self.p.get_format_from_width(sw),
            channels=ch,
            rate=rate,
            output=True,
            output_device_index=self.device_index,
        )
        chunk = 4096
        for i in range(0, len(raw), chunk):
            stream.write(raw[i : i + chunk])
        stream.stop_stream()
        stream.close()

    def close(self):
        self.p.terminate()

    async def play_from_text(
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
    ):
        """使用指定参数播放文本转语音"""
        # 从配置中获取 API URL
        url = config_manager.config.api_url
        format_text = str(text)
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
            response = await client.post(url, json=data)
            response.raise_for_status()
            logger.info(f"播放音频: {text}")

            # 播放音频
            self.play_bytes(response.content)

            return response.content
