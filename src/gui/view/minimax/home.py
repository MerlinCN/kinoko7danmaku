"""MiniMax 主页（占位）"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import SubtitleLabel, TitleLabel


class MinimaxHomeInterface(QWidget):
    """MiniMax 主页（占位）"""

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化 MiniMax 主页

        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 36, 36, 36)

        title = TitleLabel("MiniMax TTS")
        layout.addWidget(title)

        placeholder = SubtitleLabel("欢迎使用 MiniMax TTS 服务")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(placeholder, 1, Qt.AlignmentFlag.AlignCenter)
