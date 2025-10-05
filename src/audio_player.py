import io
import tempfile
from pathlib import Path
from typing import Optional

import gradio as gr
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
        # 如果没有输出设备就报错
        if len(all_devices) == 0:
            raise RuntimeError("没有找到输出设备")
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

        stream = None
        try:
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
        finally:
            if stream:
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
        format_text = text
        for k, v in config_manager.config.alias.items():
            format_text = format_text.replace(k, v)
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
            response = await client.post(url, json=data, timeout=10)
            response.raise_for_status()
            logger.info(f"播放音频: {format_text}")

            # 播放音频
            self.play_bytes(response.content)

            return response.content


# ============================================================================
# 全局实例管理和辅助功能
# ============================================================================

# 全局 StreamPlayer 实例
_stream_player = StreamPlayer()

# 存储临时文件列表用于清理 (使用 pathlib.Path)
temp_files: list[Path] = []


def cleanup_temp_file(file_path: Path):
    """清理临时文件"""
    try:
        if file_path and file_path.exists():
            file_path.unlink()
            if file_path in temp_files:
                temp_files.remove(file_path)
    except Exception as e:
        logger.warning(f"清理临时文件失败: {e}")


def cleanup_all_temp_files():
    """清理所有临时文件"""
    for file_path in temp_files.copy():
        cleanup_temp_file(file_path)


async def play_audio_with_params(
    text: str,
    chunk_length: int,
    seed: int,
    use_memory_cache: str,
    normalize: bool,
    streaming: bool,
    max_new_tokens: int,
    top_p: float,
    repetition_penalty: float,
    temperature: float,
) -> Optional[str]:
    """使用指定参数播放音频"""
    if not text.strip():
        return "❌ 请输入要播放的文本"

    try:
        # 使用指定参数播放并获取音频数据
        audio_data = await _stream_player.play_from_text(
            text=text,
            chunk_length=chunk_length,
            seed=seed,
            use_memory_cache=use_memory_cache,
            normalize=normalize,
            streaming=streaming,
            max_new_tokens=max_new_tokens,
            top_p=top_p,
            repetition_penalty=repetition_penalty,
            temperature=temperature,
        )

        status_msg = f"✅ 成功播放音频: {text[:50]}{'...' if len(text) > 50 else ''}"
        gr.Info(status_msg)

        # 将音频数据保存为临时文件
        if audio_data:
            # 使用pathlib创建临时文件
            temp_dir = Path(tempfile.gettempdir())
            # 创建带有唯一名称的临时文件路径
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".wav", dir=temp_dir
            ) as temp_file:
                temp_file_path = Path(temp_file.name)

            # 写入音频数据
            temp_file_path.write_bytes(audio_data)

            # 添加到临时文件列表
            temp_files.append(temp_file_path)

            return str(temp_file_path)  # Gradio需要字符串路径
        else:
            return None

    except Exception as e:
        error_msg = f"❌ 播放失败: {str(e)}"
        logger.error(error_msg)
        gr.Error(error_msg)
        return None


def get_stream_player():
    """获取全局 StreamPlayer 实例"""
    return _stream_player


def close_stream_player():
    """关闭 StreamPlayer 并清理资源"""
    _stream_player.close()
    cleanup_all_temp_files()
