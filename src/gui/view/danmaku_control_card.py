"""弹幕控制卡片组件"""

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QListWidget,
    QListWidgetItem,
)
from qfluentwidgets import CardWidget, BodyLabel, CaptionLabel
from loguru import logger


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
        self.title_label = BodyLabel("弹幕监听")
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()

        # 状态指示器
        self.status_label = CaptionLabel("状态: 已断开 ⭕")
        self.status_label.setStyleSheet("color: #999999;")
        title_layout.addWidget(self.status_label)

        self.main_layout.addLayout(title_layout)

        # 控制按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        self.start_btn = QPushButton("启动监听")
        self.start_btn.setFixedWidth(100)
        self.start_btn.clicked.connect(self._on_start_listening)
        button_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("停止监听")
        self.stop_btn.setFixedWidth(100)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop_listening)
        button_layout.addWidget(self.stop_btn)

        self.reconnect_btn = QPushButton("断线重连")
        self.reconnect_btn.setFixedWidth(100)
        self.reconnect_btn.clicked.connect(self._on_reconnect)
        button_layout.addWidget(self.reconnect_btn)

        button_layout.addStretch()
        self.main_layout.addLayout(button_layout)

        # 弹幕列表
        danmaku_label = CaptionLabel("实时弹幕:")
        self.main_layout.addWidget(danmaku_label)

        self.danmaku_list = QListWidget()
        self.danmaku_list.setMaximumHeight(200)
        self.danmaku_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #e1e1e1;
                border-radius: 4px;
                background: #f9f9f9;
                padding: 8px;
            }
            QListWidget::item {
                padding: 4px;
                border-radius: 2px;
            }
            QListWidget::item:hover {
                background: #f0f0f0;
            }
        """)
        self.main_layout.addWidget(self.danmaku_list)

    def _setup_signals(self) -> None:
        """设置信号连接"""
        # 这里会在 HomePanel 中连接
        pass

    def _on_start_listening(self) -> None:
        """启动监听"""
        self.start_listening.emit()
        self.is_listening = True
        self._update_status(True)

    def _on_stop_listening(self) -> None:
        """停止监听"""
        self.stop_listening.emit()
        self.is_listening = False
        self._update_status(False)

    def _on_reconnect(self) -> None:
        """断线重连"""
        if self.is_listening:
            self.stop_listening.emit()
            # 等待一下，然后重新启动
            QTimer.singleShot(500, self.start_listening.emit)

    def _update_status(self, is_connected: bool) -> None:
        """更新连接状态"""
        if is_connected:
            self.status_label.setText("状态: 已连接 🟢")
            self.status_label.setStyleSheet("color: #52cc00;")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        else:
            self.status_label.setText("状态: 已断开 ⭕")
            self.status_label.setStyleSheet("color: #999999;")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def add_danmaku(self, user_name: str, message: str, timestamp: str = "") -> None:
        """添加弹幕到列表

        Args:
            user_name: 用户名
            message: 弹幕内容
            timestamp: 时间戳（可选）
        """
        if timestamp:
            text = f"{timestamp} {user_name}: {message}"
        else:
            text = f"{user_name}: {message}"

        item = QListWidgetItem(text)
        self.danmaku_list.addItem(item)

        # 自动滚动到底部
        self.danmaku_list.scrollToBottom()

        # 限制列表长度，最多显示 100 条
        if self.danmaku_list.count() > 100:
            self.danmaku_list.takeItem(0)

    def clear_danmaku(self) -> None:
        """清空弹幕列表"""
        self.danmaku_list.clear()

    def set_connected(self, connected: bool) -> None:
        """设置连接状态

        Args:
            connected: 是否已连接
        """
        self.is_listening = connected
        self._update_status(connected)
