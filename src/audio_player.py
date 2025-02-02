import io
import logging

import aiohttp
import pyaudio
from pydub import AudioSegment

from config import gConfig

logger = logging.getLogger("kinoko7danmaku")


class AudioPlayer:
    def __init__(self):
        self.pyaudio_instance = pyaudio.PyAudio()
        self.device_name = ""
        device_index = -1
        if gConfig.debug:  # 调试模式下用VoiceMeeter输出
            for i in range(self.pyaudio_instance.get_device_count()):
                device_info = self.pyaudio_instance.get_device_info_by_index(i)
                if device_info['maxOutputChannels'] > 0 and "VoiceMeeter".lower() in device_info['name'].lower():
                    self.device_name = device_info['name']
                    device_index = i
                    logger.info(f"使用VoiceMeeter：{device_index} {self.device_name}")
                    break
        elif gConfig.voice_channel == -1:
            default_device_info = self.pyaudio_instance.get_default_output_device_info()
            device_index = default_device_info['index']
            self.device_name = default_device_info['name']
            logger.info(f"使用默认音频设备：{device_index} {self.device_name}")
        else:
            device_index = gConfig.voice_channel
            device_info = self.pyaudio_instance.get_device_info_by_index(device_index)
            self.device_name = device_info['name']
            logger.info(f"使用音频设备：{device_index} {self.device_name}")
        assert device_index != -1, "找不到音频设备"
        self.device_index = device_index
        self.stream = None

    def open_stream(self, sample_rate, channels, sample_width):
        if self.stream is not None:
            self.close_stream()
        self.stream = self.pyaudio_instance.open(
            format=self.pyaudio_instance.get_format_from_width(sample_width),
            channels=channels,
            rate=sample_rate,
            output=True,
            output_device_index=self.device_index
        )

    def play(self, audio_data):
        if self.stream is not None:
            self.stream.write(audio_data)
        else:
            raise RuntimeError("Audio stream is not open")

    async def play_online_wav(self, wav_url):
        if wav_url.startswith("data:audio/wav;base64,"):
            # 处理内嵌的 base64 wav 数据
            import base64, io
            header, encoded = wav_url.split(",", 1)
            data = base64.b64decode(encoded)
            from pydub import AudioSegment
            audio = AudioSegment.from_file(io.BytesIO(data), format="wav")
            self.open_stream(audio.frame_rate, audio.channels, audio.sample_width)
            self.play(audio.raw_data)
            return

        async with aiohttp.ClientSession() as s:
            async with s.get(wav_url) as resp:
                if resp.status != 200:
                    logger.error(f"音频下载失败，状态码：{resp.status}")
                    return
                try:
                    data = await resp.read()
                    audio = AudioSegment.from_file(io.BytesIO(data), format="wav")
                    # 确保音频流已经打开
                    self.open_stream(audio.frame_rate, audio.channels, audio.sample_width)
                    # 播放音频
                    self.play(audio.raw_data)

                except Exception as e:
                    logger.error(f"播放音频失败，error: {e}")
                    return

    def close_stream(self):
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

    def __del__(self):
        if self.stream is not None:
            self.close_stream()
        self.pyaudio_instance.terminate()


if "gAudioPlayer" not in globals():
    gAudioPlayer = AudioPlayer()
