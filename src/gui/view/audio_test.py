"""音频测试界面"""

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qasync import asyncSlot
from qfluentwidgets import (
    CardWidget,
    TextEdit,
    TitleLabel,
    ToolButton,
)
from qfluentwidgets import (
    FluentIcon as FIF,
)

from core.player import audio_player
from tts_service import get_tts_service


class AudioTestInterface(QWidget):
    """音频测试界面

    用于测试 TTS 语音合成功能。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self._init_ui()
        self._connect_signals()

    def _connect_signals(self) -> None:
        """连接信号"""
        self.test_button.clicked.connect(self._on_test_button_clicked)

    def _init_ui(self) -> None:
        """初始化 UI"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(36, 36, 36, 36)

        # 标题
        self.title_label = TitleLabel("音频测试")
        main_layout.addWidget(self.title_label)

        # 卡片
        self.test_card = CardWidget(self)
        card_layout = QVBoxLayout(self.test_card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)

        # 多行文本输入框
        self.text_edit = TextEdit()
        self.text_edit.setPlaceholderText("请输入要测试的文本...")
        self.text_edit.setMinimumHeight(200)
        card_layout.addWidget(self.text_edit)

        # 按钮布局（右下角）
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.test_button = ToolButton(FIF.PLAY)
        button_layout.addWidget(self.test_button)
        card_layout.addLayout(button_layout)

        main_layout.addWidget(self.test_card)
        main_layout.addStretch()

    @asyncSlot()
    async def _on_test_button_clicked(self) -> None:
        """测试按钮点击事件"""
        text = self.text_edit.toPlainText()
        if not text:
            return
        tts_service = get_tts_service()
        audio = await tts_service.text_to_speech(text)
        await audio_player.play_bytes_async(audio)
