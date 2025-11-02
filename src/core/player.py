import io
import wave
from pathlib import Path

import pyaudio
import sounddevice as sd
from loguru import logger

from models.device import OutputDevice


class StreamPlayer:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.device_index = sd.default.device[1]

    @property
    def default_output_index(self) -> int:
        return sd.default.device[1]

    def get_output_devices(self) -> list[OutputDevice]:
        """获取设备选择列表（使用sounddevice）- 返回元组列表格式"""

        # 获取所有设备
        all_devices: list[dict] = sd.query_devices()  # type: ignore
        # 如果没有输出设备就报错
        if len(all_devices) == 0:
            raise RuntimeError("没有找到输出设备")
        default_output_index: int = sd.default.device[1]  # type: ignore

        default_output_device: dict = all_devices[default_output_index]  # type: ignore

        choices = []

        default_api: str = sd.query_hostapis()[default_output_device["hostapi"]]["name"]  # type: ignore
        # 遍历所有设备，只添加纯输出设备
        for idx, device in enumerate(all_devices):
            if device["max_output_channels"] <= 0:
                continue
            name = device["name"]
            api_name: str = sd.query_hostapis()[device["hostapi"]]["name"]  # type: ignore
            if default_api not in api_name:
                continue
            choices.append(OutputDevice(index=idx, name=name))  # (显示名称, 实际索引)

        return choices

    def set_output_device_by_name(self, device_name: str):
        """根据设备名称设置输出设备"""
        for device in self.get_output_devices():
            if device_name in device.name:
                self.set_output_device(device.index)
                return
        logger.error(f"未找到设备: {device_name}")

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
            logger.exception(f"设置设备失败: {e}")
            return False

    def play_bytes(self, audio_bytes: bytes):
        """播放音频字节流（WAV 格式）

        Args:
            audio_bytes: WAV 格式的音频字节流
        """
        # 使用 wave 模块解析 WAV 文件
        with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
            # 获取音频参数
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            frame_rate = wf.getframerate()

            # 读取所有音频数据
            raw_data = wf.readframes(wf.getnframes())

        # 使用 pyaudio 播放音频
        stream = None
        try:
            stream = self.p.open(
                format=self.p.get_format_from_width(sample_width),
                channels=channels,
                rate=frame_rate,
                output=True,
                output_device_index=self.device_index,
            )
            # 分块写入音频数据
            chunk = 4096
            for i in range(0, len(raw_data), chunk):
                stream.write(raw_data[i : i + chunk])
            stream.stop_stream()
        finally:
            if stream:
                stream.close()

    def close(self):
        self.p.terminate()


# ============================================================================
# 全局实例和辅助功能
# ============================================================================

# 全局 StreamPlayer 单例实例
audio_player = StreamPlayer()

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


def close_audio_player():
    """关闭 StreamPlayer 并清理资源"""
    audio_player.close()
    cleanup_all_temp_files()
