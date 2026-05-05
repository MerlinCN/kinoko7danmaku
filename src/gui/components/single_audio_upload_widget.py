"""单文件音频上传组件"""

from pathlib import Path

from loguru import logger
from mutagen import File as MutagenFile
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QVBoxLayout, QWidget
from qasync import asyncSlot
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    InfoBar,
    InfoBarPosition,
    PrimaryPushButton,
    StateToolTip,
    ToolButton,
)
from qfluentwidgets import FluentIcon as FIF

from models.minimax import FilePurpose, FileUploadResponse
from tts_service.minimax import MinimaxService


class SingleAudioUploadWidget(CardWidget):
    """单文件音频上传组件"""

    fileUploaded = Signal(FileUploadResponse, float)  # 文件上传成功信号（响应, 时长秒）
    fileRemoved = Signal()  # 文件删除信号

    def __init__(
        self,
        parent: QWidget | None = None,
        min_duration: float = 10.0,
        max_duration: float = 300.0,
        max_size_mb: float = 20.0,
        tip_text: str | None = None,
        purpose: FilePurpose = FilePurpose.VOICE_CLONE,
    ) -> None:
        """初始化单文件音频上传组件

        Args:
            parent: 父窗口
            min_duration: 最小时长（秒），默认10秒
            max_duration: 最大时长（秒），默认300秒（5分钟）
            max_size_mb: 最大文件大小（MB），默认20MB
            tip_text: 提示文本，为 None 时使用默认文本
            purpose: 文件上传用途，源音频用 VOICE_CLONE，示例音频用 PROMPT_AUDIO
        """
        super().__init__(parent)
        self._tts_service = MinimaxService()
        self._uploaded_file: FileUploadResponse | None = None
        self._uploaded_duration: float = 0.0
        self._is_uploading = False

        # 验证参数
        self._min_duration = min_duration
        self._max_duration = max_duration
        self._max_size_mb = max_size_mb
        self._tip_text = tip_text
        self._purpose = purpose

        self._init_ui()

    def _init_ui(self) -> None:
        """初始化 UI"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(12)

        # 上传按钮
        button_layout = QHBoxLayout()
        self.upload_button = PrimaryPushButton(FIF.FOLDER, "选择音频文件")
        self.upload_button.clicked.connect(self._on_upload_button_clicked)
        button_layout.addWidget(self.upload_button)
        button_layout.addStretch()
        self.main_layout.addLayout(button_layout)

        # 提示信息
        if self._tip_text is None:
            # 默认提示文本
            if self._min_duration == 0:
                tip_text = f"支持 mp3/m4a/wav 格式，最长{self._max_duration:.0f}秒，最大{self._max_size_mb:.0f}MB"
            else:
                tip_text = f"支持 mp3/m4a/wav 格式，{self._min_duration:.0f}秒-{self._max_duration / 60:.0f}分钟，最大{self._max_size_mb:.0f}MB"
        else:
            tip_text = self._tip_text

        self.tip_label = CaptionLabel(tip_text)
        self.tip_label.setTextColor("#606060", "#d2d2d2")
        self.main_layout.addWidget(self.tip_label)

        # 已上传文件信息卡片（初始隐藏）
        self.file_info_widget = QWidget()
        self.file_info_layout = QHBoxLayout(self.file_info_widget)
        self.file_info_layout.setContentsMargins(0, 0, 0, 0)
        self.file_info_layout.setSpacing(10)

        # 文件信息
        file_info_v_layout = QVBoxLayout()
        file_info_v_layout.setSpacing(2)

        self.file_name_label = BodyLabel("")
        file_info_v_layout.addWidget(self.file_name_label)

        self.file_details_label = CaptionLabel("")
        self.file_details_label.setTextColor("#606060", "#d2d2d2")
        file_info_v_layout.addWidget(self.file_details_label)

        self.file_info_layout.addLayout(file_info_v_layout)
        self.file_info_layout.addStretch()

        # 删除按钮
        self.delete_button = ToolButton(FIF.DELETE)
        self.delete_button.setFixedSize(28, 28)
        self.delete_button.setToolTip("删除")
        self.delete_button.clicked.connect(self._on_delete_clicked)
        self.file_info_layout.addWidget(self.delete_button)

        self.main_layout.addWidget(self.file_info_widget)
        self.file_info_widget.hide()  # 初始隐藏

    def _on_upload_button_clicked(self) -> None:
        """上传按钮点击事件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择音频文件",
            "",
            "音频文件 (*.mp3 *.m4a *.wav);;所有文件 (*)",
        )

        if file_path:
            # 异步上传文件
            self._upload_file(file_path)

    def _validate_audio_file(self, file_path: str) -> tuple[bool, str, float]:
        """验证音频文件

        Args:
            file_path: 文件路径

        Returns:
            (是否有效, 错误消息, 音频时长秒)
        """
        file = Path(file_path)

        # 检查格式
        allowed_extensions = {".mp3", ".m4a", ".wav"}
        if file.suffix.lower() not in allowed_extensions:
            return False, f"不支持的格式：{file.suffix}，仅支持 mp3/m4a/wav", 0.0

        # 检查大小
        max_size = self._max_size_mb * 1024 * 1024
        file_size = file.stat().st_size
        if file_size > max_size:
            size_mb = file_size / 1024 / 1024
            return (
                False,
                f"文件过大：{size_mb:.2f}MB，最大支持 {self._max_size_mb:.0f}MB",
                0.0,
            )

        # 检查时长
        try:
            audio = MutagenFile(file_path)
            if audio is None or audio.info is None:
                return False, "无法读取音频信息", 0.0

            duration = audio.info.length

            if self._min_duration > 0 and duration < self._min_duration:
                return (
                    False,
                    f"音频时长过短：{duration:.1f}秒，需要至少 {self._min_duration:.0f}秒",
                    0.0,
                )
            if duration > self._max_duration:
                max_display = (
                    f"{self._max_duration / 60:.0f}分钟"
                    if self._max_duration >= 60
                    else f"{self._max_duration:.0f}秒"
                )
                return (
                    False,
                    f"音频时长过长：{duration:.1f}秒，最多支持 {max_display}",
                    0.0,
                )

        except Exception as e:
            logger.exception(f"检查音频时长失败: {e}")
            return False, f"读取音频信息失败：{e}", 0.0

        return True, "", duration

    @asyncSlot()
    async def _upload_file(self, file_path: str) -> None:
        """异步上传文件

        Args:
            file_path: 文件路径
        """
        # 防止重复上传
        if self._is_uploading:
            return

        # 验证文件
        is_valid, error_msg, duration = self._validate_audio_file(file_path)
        if not is_valid:
            InfoBar.warning(
                title="文件验证失败",
                content=error_msg,
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self.window(),
            )
            return

        self._is_uploading = True
        self.upload_button.setEnabled(False)

        # 显示上传状态
        state_tooltip = StateToolTip(
            "上传中", f"正在上传 {Path(file_path).name}...", self.window()
        )
        state_tooltip.move(state_tooltip.getSuitablePos())
        state_tooltip.show()

        try:
            # 调用上传 API
            response = await self._tts_service.upload_audio_file(
                file_path, purpose=self._purpose
            )

            # 保存上传结果
            self._uploaded_file = response
            self._uploaded_duration = duration

            # 显示文件信息
            self._show_file_info(response, duration)

            # 发射信号
            self.fileUploaded.emit(response, duration)

            state_tooltip.setState(True)
            state_tooltip.setTitle("上传成功")
            logger.info(
                f"文件上传成功: {response.file.filename} (file_id: {response.file.file_id})"
            )

        except ValueError as e:
            logger.error(f"上传失败: {e}")
            state_tooltip.setState(False)
            state_tooltip.setTitle("上传失败")
            state_tooltip.setContent(str(e))
        except Exception as e:
            logger.exception(f"上传失败: {e}")
            state_tooltip.setState(False)
            state_tooltip.setTitle("上传失败")
            state_tooltip.setContent("网络请求失败，请检查网络连接")
        finally:
            self._is_uploading = False
            self.upload_button.setEnabled(True)

    def _show_file_info(
        self, file_response: FileUploadResponse, duration: float
    ) -> None:
        """显示文件信息

        Args:
            file_response: 文件上传响应
            duration: 本地解析的音频时长（秒）
        """
        self.file_name_label.setText(file_response.file.filename)

        size_mb = file_response.file.bytes / 1024 / 1024
        duration_str = f"{duration:.1f}秒"
        details_text = f"{size_mb:.2f}MB · {duration_str}"
        self.file_details_label.setText(details_text)

        self.file_info_widget.show()
        self.upload_button.setText("重新选择")

    def _on_delete_clicked(self) -> None:
        """删除按钮点击事件"""
        self._uploaded_file = None
        self._uploaded_duration = 0.0
        self.file_info_widget.hide()
        self.upload_button.setText("选择音频文件")

        # 发射删除信号
        self.fileRemoved.emit()

        InfoBar.success(
            title="删除成功",
            content="已删除文件",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=1500,
            parent=self.window(),
        )

    def get_uploaded_file(self) -> FileUploadResponse | None:
        """获取已上传的文件

        Returns:
            FileUploadResponse | None: 已上传文件，如果未上传则返回 None
        """
        return self._uploaded_file

    def clear_uploaded_file(self) -> None:
        """清空已上传文件"""
        self._uploaded_file = None
        self._uploaded_duration = 0.0
        self.file_info_widget.hide()
        self.upload_button.setText("选择音频文件")
