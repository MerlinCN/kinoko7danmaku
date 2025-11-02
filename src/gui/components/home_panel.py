"""主页面板 - 已登录界面"""

from PySide6.QtWidgets import (
    QVBoxLayout,
    QWidget,
)

from .danmaku_control_card import DanmakuControlCard
from .message_display_card import MessageDisplayCard
from .user_info_card import UserInfoCard


class HomePanel(QWidget):
    """主页面板

    已登录后显示的主界面，包含用户信息和弹幕控制功能。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self._init_ui()

    def _init_ui(self) -> None:
        """初始化 UI"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(16)

        # 用户信息卡片
        self.user_info_card = UserInfoCard()
        self.main_layout.addWidget(self.user_info_card)

        # 弹幕控制卡片
        self.danmaku_control_card = DanmakuControlCard()
        self.main_layout.addWidget(self.danmaku_control_card)

        # 消息显示卡片
        self.message_display_card = MessageDisplayCard()
        self.main_layout.addWidget(self.message_display_card)

        self.main_layout.addStretch()

    def get_user_info_card(self) -> UserInfoCard:
        """获取用户信息卡片"""
        return self.user_info_card

    def get_message_display_card(self) -> MessageDisplayCard:
        """获取消息显示卡片"""
        return self.message_display_card
