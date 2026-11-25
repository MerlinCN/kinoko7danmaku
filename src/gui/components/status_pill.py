"""状态指示组件"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget
from qfluentwidgets import BodyLabel

from models.bilibili import ConnectionState

_CONNECTION_STYLES: dict[ConnectionState, tuple[str, str]] = {
    ConnectionState.CONNECTED: ('已连接', '#2fa84f'),
    ConnectionState.CONNECTING: ('连接中', '#d99100'),
    ConnectionState.DISCONNECTED: ('未连接', '#8a8a8a'),
    ConnectionState.ERROR: ('连接异常', '#d64545'),
}


class StatusPill(QWidget):
    """圆点 + 文案的状态指示器

    用于展示连接状态或直播状态，颜色由调用方指定，不使用 emoji。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化状态指示器

        Args:
            parent: 父组件
        """
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)

        self._dot = QLabel(self)
        self._dot.setFixedSize(8, 8)
        self._text = BodyLabel('', self)

        self._layout.addWidget(self._dot, 0, Qt.AlignmentFlag.AlignVCenter)
        self._layout.addWidget(self._text, 0, Qt.AlignmentFlag.AlignVCenter)

        self.set_state(ConnectionState.DISCONNECTED)

    def set_state(self, state: ConnectionState) -> None:
        """设置连接状态

        Args:
            state: 连接状态
        """
        text, color = _CONNECTION_STYLES[state]
        self.set_status(text, color)

    def set_status(self, text: str, color: str) -> None:
        """设置自定义状态文案与颜色

        Args:
            text: 状态文案
            color: 状态颜色（十六进制）
        """
        self._dot.setStyleSheet(f'background-color: {color}; border-radius: 4px;')
        self._text.setText(text)
        self._text.setStyleSheet(f'color: {color};')
