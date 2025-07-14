import io

import httpx
import pyaudio
from loguru import logger
from pydub import AudioSegment

from config import config_manager


class StreamPlayer:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        default_device_info = self.p.get_default_output_device_info()
        self.device_index = int(default_device_info["index"])

    def get_output_devices(self):
        """获取所有输出设备列表"""
        devices = []
        device_count = self.p.get_device_count()

        for i in range(device_count):
            device_info = self.p.get_device_info_by_index(i)
            # 只返回有输出通道的设备
            if int(device_info["maxOutputChannels"]) > 0:
                devices.append(
                    {
                        "index": i,
                        "name": device_info["name"],
                        "is_default": i == self.device_index,
                    }
                )

        return devices

    def set_output_device(self, device_index: int):
        """设置输出设备"""
        try:
            device_info = self.p.get_device_info_by_index(device_index)
            if int(device_info["maxOutputChannels"]) > 0:
                self.device_index = device_index
                logger.info(f"已设置输出设备: {device_info['name']}")
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
        url = config_manager.get_api_url()
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
