"""MiniMax 音色克隆界面（占位）"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import SubtitleLabel, TitleLabel


class MinimaxVoiceCloneInterface(QWidget):
    """MiniMax 音色克隆界面（占位）"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 36, 36, 36)

        title = TitleLabel("音色克隆")
        layout.addWidget(title)

        placeholder = SubtitleLabel("功能开发中，敬请期待...")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(placeholder, 1, Qt.AlignmentFlag.AlignCenter)
