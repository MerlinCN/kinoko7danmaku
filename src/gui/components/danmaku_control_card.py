"""弹幕控制卡片组件"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)
from qasync import asyncSlot
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    PushButton,
    SubtitleLabel,
)

from bilibili import bili_service


class DanmakuControlCard(CardWidget):
    """弹幕控制卡片

    显示弹幕监听状态，提供启动/停止监听等控制按钮。
    实时显示收到的弹幕列表。
    """

    start_listening = Signal()
    stop_listening = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.is_listening = False
        self._init_ui()
        self._setup_signals()

    def _init_ui(self) -> None:
        """初始化 UI"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(12)
        self.main_layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title_layout = QHBoxLayout()
        self.title_label = SubtitleLabel('弹幕监听')
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()

        # 状态指示器
        self.status_label = BodyLabel('状态: 已断开 ⭕')
        title_layout.addWidget(self.status_label)

        self.main_layout.addLayout(title_layout)

        # 控制按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        self.start_btn = PushButton('启动监听')
        self.start_btn.setFixedWidth(100)
        self.start_btn.clicked.connect(self._on_start_listening)
        button_layout.addWidget(self.start_btn)

        self.stop_btn = PushButton('停止监听')
        self.stop_btn.setFixedWidth(100)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop_listening)
        button_layout.addWidget(self.stop_btn)

        button_layout.addStretch()
        self.main_layout.addLayout(button_layout)

    def _setup_signals(self) -> None:
        """设置信号连接"""
        # 这里会在 HomePanel 中连接

    @asyncSlot()
    async def _on_start_listening(self) -> None:
        """启动监听"""
        await bili_service.run()
        self.is_listening = True
        self._update_status(is_connected=True)

    @asyncSlot()
    async def _on_stop_listening(self) -> None:
        """停止监听"""
        await bili_service.stop()
        self.is_listening = False
        self._update_status(is_connected=False)

    def _update_status(self, is_connected: bool) -> None:
        """更新连接状态"""
        if is_connected:
            self.status_label.setText('状态: 已连接 🟢')
            self.status_label.setStyleSheet('color: #52cc00;')
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        else:
            self.status_label.setText('状态: 已断开 ⭕')
            self.status_label.setStyleSheet('color: #999999;')
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def set_connected(self, connected: bool) -> None:
        """设置连接状态

        Args:
            connected: 是否已连接
        """
        self.is_listening = connected
        self._update_status(connected)
