import asyncio

import miniaudio
import pyaudio
import sounddevice as sd

from loguru import logger

from models.device import OutputDevice


class StreamPlayer:
    def __init__(self) -> None:
        self.p = pyaudio.PyAudio()
        self.device_index = sd.default.device[1]
        self.audio_queue: asyncio.Queue[bytes] | None = None
        self.worker_task: asyncio.Task | None = None
        self.is_running = False

    @property
    def default_output_index(self) -> int:
        return sd.default.device[1]

    def get_output_devices(self) -> list[OutputDevice]:
        """获取输出设备列表

        Returns:
            可用的输出设备；系统没有任何输出设备时返回空列表
        """
        all_devices: list[dict] = sd.query_devices()  # type: ignore
        if not all_devices:
            return []

        hostapis: list[dict] = sd.query_hostapis()  # type: ignore
        default_index: int = sd.default.device[1]  # type: ignore
        # 只保留与默认设备同一套 hostapi 的条目，避免同一个设备被多个 API 重复列出
        default_api = (
            hostapis[all_devices[default_index]['hostapi']]['name']  # type: ignore
            if 0 <= default_index < len(all_devices)
            else ''
        )

        choices = []
        for index, device in enumerate(all_devices):
            if device['max_output_channels'] <= 0:
                continue
            api_name: str = hostapis[device['hostapi']]['name']  # type: ignore
            if default_api and default_api not in api_name:
                continue
            choices.append(OutputDevice(index=index, name=device['name']))

        return choices

    def get_current_output_device(self) -> OutputDevice | None:
        """获取当前输出设备

        Returns:
            OutputDevice | None: 当前设备，查询失败时返回 None
        """
        try:
            device_info: dict = sd.query_devices(self.device_index)  # type: ignore
        except Exception:
            return None
        return OutputDevice(
            index=self.device_index,
            name=device_info['name'],
            sample_rate=int(device_info['default_samplerate']),
            channels=int(device_info['max_output_channels']),
        )

    def set_output_device_by_name(self, device_name: str) -> None:
        """根据设备名称设置输出设备"""
        for device in self.get_output_devices():
            if device_name in device.name:
                self.set_output_device(device.index)
                return
        logger.error(f'未找到设备: {device_name}')

    def set_output_device(self, device_index: int) -> bool | None:
        """设置输出设备"""
        try:
            if device_index == -1:
                device_index = sd.default.device[1]  # type: ignore
            if device_index < 0:
                logger.warning('未检测到输出设备，跳过设备切换')
                return False
            device_info: dict = sd.query_devices(device_index)  # type: ignore
            if int(device_info['max_output_channels']) > 0:  # type: ignore
                logger.info(f'已设置输出设备: {device_info["name"]}')
                self.device_index = device_index
            else:
                logger.error(f'设备 {device_index} 不支持音频输出')
                return False
        except Exception as e:
            logger.exception(f'设置设备失败: {e}')
            return False
        else:
            return True

    def play_bytes(self, audio_bytes: bytes) -> None:
        """播放音频字节流（WAV/MP3 格式）

        Args:
            audio_bytes: WAV/MP3 格式的音频字节流
        """
        # 解析音频文件
        try:
            decoded_file = miniaudio.decode(audio_bytes)
        except miniaudio.DecodeError as e:
            logger.error(f'音频解码失败: {e}')
            return

        sample_width = decoded_file.sample_width
        channels = decoded_file.nchannels
        frame_rate = decoded_file.sample_rate
        raw_data = decoded_file.samples.tobytes()

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

    async def _play_worker(self) -> None:
        """后台任务：从队列中取出音频并播放"""
        if self.audio_queue is None:
            logger.error('音频队列未初始化')
            return

        while self.is_running:
            try:
                # 从队列中获取音频数据
                audio_bytes = await self.audio_queue.get()
                # 在线程中播放音频（避免阻塞）
                await asyncio.to_thread(self.play_bytes, audio_bytes)
                self.audio_queue.task_done()
            except asyncio.CancelledError:
                logger.info('音频播放队列任务已取消')
                break
            except Exception as e:
                logger.exception(f'播放音频时出错: {e}')

    def start_worker(self) -> None:
        """启动音频播放队列处理任务"""
        if not self.is_running:
            # 在事件循环运行时创建队列，避免在 __init__ 中创建导致 RuntimeError
            self.audio_queue = asyncio.Queue()
            self.is_running = True
            self.worker_task = asyncio.create_task(self._play_worker())
            logger.info('音频播放队列已启动')

    async def stop_worker(self) -> None:
        """停止音频播放队列处理任务"""
        if self.is_running:
            self.is_running = False
            if self.worker_task:
                self.worker_task.cancel()
                try:
                    await self.worker_task
                except asyncio.CancelledError:
                    pass
            # 清空队列
            if self.audio_queue is not None:
                while not self.audio_queue.empty():
                    try:
                        self.audio_queue.get_nowait()
                        self.audio_queue.task_done()
                    except asyncio.QueueEmpty:
                        break
                self.audio_queue = None
            logger.info('音频播放队列已停止')

    async def play_bytes_async(self, audio_bytes: bytes) -> None:
        """异步方式播放音频（添加到队列）

        Args:
            audio_bytes: WAV 格式的音频字节流
        """
        if self.audio_queue is None:
            logger.error('音频队列未初始化，请先调用 start_worker()')
            return
        await self.audio_queue.put(audio_bytes)

    def close(self) -> None:
        self.p.terminate()


# ============================================================================
# 全局实例和辅助功能
# ============================================================================

# 全局 StreamPlayer 单例实例
audio_player = StreamPlayer()
