"""会话统计卡片组件"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import CaptionLabel, CardWidget, IconWidget, TitleLabel
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets.common.icon import FluentIconBase

from models.bilibili import SessionStats


class StatCard(CardWidget):
    """单个统计卡片"""

    def __init__(
        self,
        icon: str | QIcon | FluentIconBase,
        title: str,
        color: str,
        parent: QWidget | None = None,
    ) -> None:
        """初始化统计卡片

        Args:
            icon: 图标
            title: 统计项名称
            color: 数值颜色
            parent: 父组件
        """
        super().__init__(parent)
        self.setMinimumHeight(84)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(14)

        icon_widget = IconWidget(icon, self)
        icon_widget.setFixedSize(24, 24)
        layout.addWidget(icon_widget, 0, Qt.AlignmentFlag.AlignVCenter)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        title_label = CaptionLabel(title, self)
        self.value_label = TitleLabel('0', self)
        self.value_label.setTextColor(QColor(color), QColor(color))

        info_layout.addWidget(title_label)
        info_layout.addWidget(self.value_label)
        layout.addLayout(info_layout, 1)

    def set_value(self, value: int) -> None:
        """更新数值

        Args:
            value: 新数值
        """
        self.value_label.setText(f'{value:,}')


class StatsRow(QWidget):
    """会话统计行"""

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化统计行

        Args:
            parent: 父组件
        """
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.danmaku_card = StatCard(FIF.CHAT, '弹幕', '#3b82f6', self)
        self.gift_card = StatCard(FIF.HEART, '礼物', '#e8792b', self)
        self.guard_card = StatCard(FIF.CERTIFICATE, '舰长', '#8b5cf6', self)
        self.super_chat_card = StatCard(FIF.MEGAPHONE, '醒目留言', '#d4a017', self)

        for card in (self.danmaku_card, self.gift_card, self.guard_card, self.super_chat_card):
            layout.addWidget(card, 1)

    def update_stats(self, stats: SessionStats) -> None:
        """刷新统计数据

        Args:
            stats: 会话统计
        """
        self.danmaku_card.set_value(stats.danmaku)
        self.gift_card.set_value(stats.gift)
        self.guard_card.set_value(stats.guard)
        self.super_chat_card.set_value(stats.super_chat)
