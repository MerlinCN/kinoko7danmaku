"""消息显示卡片组件"""

from collections import deque
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CardWidget, SubtitleLabel


class MessageDisplayCard(CardWidget):
    """消息显示卡片

    显示最近的消息，固定显示 5 行，采用队列模式（先进先出）。
    """

    def __init__(self, parent: QWidget | None = None, max_lines: int = 5) -> None:
        """初始化消息显示卡片

        Args:
            parent: 父组件
            max_lines: 最大显示行数
        """
        super().__init__(parent=parent)
        self.max_lines = max_lines
        self.messages = deque(maxlen=max_lines)  # 使用 deque 实现固定长度队列
        self.message_labels = []  # 存储标签组件
        self._init_ui()

    def _init_ui(self) -> None:
        """初始化 UI"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(12)

        # 标题
        self.title_label = SubtitleLabel("消息记录")
        self.main_layout.addWidget(self.title_label)

        # 创建消息标签（固定 5 行）
        for i in range(self.max_lines):
            label = BodyLabel("")
            label.setWordWrap(True)  # 允许换行
            label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self.message_labels.append(label)
            self.main_layout.addWidget(label)

    def add_message(self, message: str) -> None:
        """添加一条消息

        Args:
            message: 消息内容
        """
        # 添加到队列（自动移除最旧的消息）
        self.messages.append(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]:{message}"
        )

        # 更新显示
        self._update_display()

    def clear_messages(self) -> None:
        """清空所有消息"""
        self.messages.clear()
        self._update_display()

    def _update_display(self) -> None:
        """更新显示内容"""
        # 将队列中的消息显示到标签上
        for i, label in enumerate(self.message_labels):
            if i < len(self.messages):
                label.setText(self.messages[i])
            else:
                label.setText("")  # 清空未使用的标签
