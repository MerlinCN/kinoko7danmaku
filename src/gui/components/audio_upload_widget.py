"""音频上传组件"""

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
    FlowLayout,
    InfoBar,
    InfoBarPosition,
    PrimaryPushButton,
    StateToolTip,
    ToolButton,
)
from qfluentwidgets import FluentIcon as FIF

from models.minimax import FileUploadResponse
from tts_service.minimax import MinimaxService


class UploadedFileCard(CardWidget):
    """已上传文件卡片"""

    deleteClicked = Signal(str)  # 删除按钮点击信号 (file_id)

    def __init__(
        self,
        file_id: str,
        file_name: str,
        file_size: int,
        duration: float,
        parent: QWidget | None = None,
    ) -> None:
        """初始化已上传文件卡片

        Args:
            file_id: 文件ID
            file_name: 文件名
            file_size: 文件大小（字节）
            duration: 音频时长（秒）
            parent: 父窗口
        """
        super().__init__(parent)
        self.file_id = file_id
        self.file_name = file_name
        self.file_size = file_size
        self.duration = duration

        self._init_ui()

    def _init_ui(self) -> None:
        """初始化 UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 8, 8)
        layout.setSpacing(10)

        # 左侧：文件信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        # 文件名
        name_label = BodyLabel(self.file_name)
        info_layout.addWidget(name_label)

        # 文件详情（大小 + 时长）
        size_mb = self.file_size / 1024 / 1024
        duration_str = f"{self.duration:.1f}秒"
        details_text = f"{size_mb:.2f}MB · {duration_str}"
        details_label = CaptionLabel(details_text)
        details_label.setTextColor("#606060", "#d2d2d2")
        info_layout.addWidget(details_label)

        layout.addLayout(info_layout)
        layout.addStretch()

        # 右侧：删除按钮
        delete_button = ToolButton(FIF.DELETE)
        delete_button.setFixedSize(28, 28)
        delete_button.setToolTip("删除")
        delete_button.clicked.connect(lambda: self.deleteClicked.emit(self.file_id))
        layout.addWidget(delete_button)

        self.setFixedHeight(60)


class AudioUploadWidget(CardWidget):
    """音频上传组件"""

    fileUploaded = Signal(FileUploadResponse)  # 文件上传成功信号

    def __init__(
        self,
        parent: QWidget | None = None,
        min_duration: float = 10.0,
        max_duration: float = 300.0,
        max_size_mb: float = 20.0,
        tip_text: str | None = None,
    ) -> None:
        """初始化音频上传组件

        Args:
            parent: 父窗口
            min_duration: 最小时长（秒），默认10秒
            max_duration: 最大时长（秒），默认300秒（5分钟）
            max_size_mb: 最大文件大小（MB），默认20MB
            tip_text: 提示文本，为 None 时使用默认文本
        """
        super().__init__(parent)
        self._tts_service = MinimaxService()
        self._uploaded_files: list[FileUploadResponse] = []
        self._is_uploading = False

        # 验证参数
        self._min_duration = min_duration
        self._max_duration = max_duration
        self._max_size_mb = max_size_mb
        self._tip_text = tip_text

        self._init_ui()

    def _init_ui(self) -> None:
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # 上传按钮
        button_layout = QHBoxLayout()
        self.upload_button = PrimaryPushButton(FIF.FOLDER, "选择音频文件")
        self.upload_button.clicked.connect(self._on_upload_button_clicked)
        button_layout.addWidget(self.upload_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        # 提示信息
        if self._tip_text is None:
            # 默认提示文本
            if self._min_duration == 0:
                tip_text = f"支持 mp3/m4a/wav 格式，最长{self._max_duration:.0f}秒，最大{self._max_size_mb:.0f}MB"
            else:
                tip_text = f"支持 mp3/m4a/wav 格式，{self._min_duration:.0f}秒-{self._max_duration / 60:.0f}分钟，最大{self._max_size_mb:.0f}MB"
        else:
            tip_text = self._tip_text

        tip_label = CaptionLabel(tip_text)
        tip_label.setTextColor("#606060", "#d2d2d2")
        layout.addWidget(tip_label)

        # 已上传文件列表容器
        self.file_list_container = QWidget()
        self.file_list_layout = FlowLayout(self.file_list_container, needAni=True)
        self.file_list_layout.setContentsMargins(0, 0, 0, 0)
        self.file_list_layout.setHorizontalSpacing(10)
        self.file_list_layout.setVerticalSpacing(10)
        layout.addWidget(self.file_list_container)

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

    def _validate_audio_file(self, file_path: str) -> tuple[bool, str]:
        """验证音频文件

        Args:
            file_path: 文件路径

        Returns:
            (是否有效, 错误消息)
        """
        file = Path(file_path)

        # 检查格式
        allowed_extensions = {".mp3", ".m4a", ".wav"}
        if file.suffix.lower() not in allowed_extensions:
            return False, f"不支持的格式：{file.suffix}，仅支持 mp3/m4a/wav"

        # 检查大小
        max_size = self._max_size_mb * 1024 * 1024
        file_size = file.stat().st_size
        if file_size > max_size:
            size_mb = file_size / 1024 / 1024
            return (
                False,
                f"文件过大：{size_mb:.2f}MB，最大支持 {self._max_size_mb:.0f}MB",
            )

        # 检查时长
        try:
            audio = MutagenFile(file_path)
            if audio is None or audio.info is None:
                return False, "无法读取音频信息"

            duration = audio.info.length

            if self._min_duration > 0 and duration < self._min_duration:
                return (
                    False,
                    f"音频时长过短：{duration:.1f}秒，需要至少 {self._min_duration:.0f}秒",
                )
            if duration > self._max_duration:
                max_display = (
                    f"{self._max_duration / 60:.0f}分钟"
                    if self._max_duration >= 60
                    else f"{self._max_duration:.0f}秒"
                )
                return False, f"音频时长过长：{duration:.1f}秒，最多支持 {max_display}"

        except Exception as e:
            logger.exception(f"检查音频时长失败: {e}")
            return False, f"读取音频信息失败：{e}"

        return True, ""

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
        is_valid, error_msg = self._validate_audio_file(file_path)
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
            response = await self._tts_service.upload_audio_file(file_path)

            # 保存上传结果
            self._uploaded_files.append(response)

            # 添加到已上传列表
            self._add_uploaded_file_card(response)

            # 发射信号
            self.fileUploaded.emit(response)

            state_tooltip.setState(True)
            state_tooltip.setTitle("上传成功")
            logger.info(
                f"文件上传成功: {response.file_name} (file_id: {response.file_id})"
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

    def _add_uploaded_file_card(self, file_response: FileUploadResponse) -> None:
        """添加已上传文件卡片

        Args:
            file_response: 文件上传响应
        """
        card = UploadedFileCard(
            file_id=file_response.file_id,
            file_name=file_response.file_name,
            file_size=file_response.file_size,
            duration=file_response.duration,
            parent=self.file_list_container,
        )
        card.setFixedWidth(400)
        card.deleteClicked.connect(self._on_file_delete_clicked)
        self.file_list_layout.addWidget(card)

    def _on_file_delete_clicked(self, file_id: str) -> None:
        """删除文件按钮点击事件

        Args:
            file_id: 文件ID
        """
        # 从列表中移除
        self._uploaded_files = [f for f in self._uploaded_files if f.file_id != file_id]

        # 从 UI 中移除
        for i in range(self.file_list_layout.count()):
            widget = self.file_list_layout.itemAt(i).widget()
            if isinstance(widget, UploadedFileCard) and widget.file_id == file_id:
                self.file_list_layout.removeWidget(widget)
                widget.deleteLater()
                break

        InfoBar.success(
            title="删除成功",
            content="已删除文件",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=1500,
            parent=self.window(),
        )

    def get_uploaded_files(self) -> list[FileUploadResponse]:
        """获取已上传的文件列表

        Returns:
            list[FileUploadResponse]: 已上传文件列表
        """
        return self._uploaded_files

    def clear_uploaded_files(self) -> None:
        """清空已上传文件列表"""
        self._uploaded_files.clear()

        # 清空 UI
        for i in reversed(range(self.file_list_layout.count())):
            widget = self.file_list_layout.itemAt(i).widget()
            if widget:
                self.file_list_layout.removeWidget(widget)
                widget.deleteLater()
