"""音频输出卡片"""

from PySide6.QtCore import Signal
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CardWidget, PushButton, SubtitleLabel

from core.player import audio_player


class AudioOutputCard(CardWidget):
    """音频输出卡片

    展示当前输出设备，并提供测试与切换设备入口。
    """

    open_audio_test = Signal()
    open_settings = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化音频输出卡片

        Args:
            parent: 父组件
        """
        super().__init__(parent)
        self._init_ui()
        self.refresh()

    def _init_ui(self) -> None:
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        layout.addWidget(SubtitleLabel('音频输出', self))

        self.device_label = BodyLabel('--', self)
        layout.addWidget(self.device_label)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        self.test_btn = PushButton('测试音', self)
        self.test_btn.clicked.connect(self._on_test_clicked)
        button_layout.addWidget(self.test_btn)

        self.switch_btn = PushButton('更换设备', self)
        self.switch_btn.clicked.connect(self._on_switch_clicked)
        button_layout.addWidget(self.switch_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

    def refresh(self) -> None:
        """刷新当前输出设备"""
        device = audio_player.get_current_output_device()
        self.device_label.setText(device.name if device else '未检测到输出设备')
        self.device_label.setToolTip(device.name if device else '')

    def _on_test_clicked(self, _checked: bool = False) -> None:
        """打开音频测试页"""
        self.open_audio_test.emit()

    def _on_switch_clicked(self, _checked: bool = False) -> None:
        """打开设置页"""
        self.open_settings.emit()

    def showEvent(self, event: QShowEvent) -> None:
        """页面显示时刷新设备信息"""
        super().showEvent(event)
        self.refresh()
