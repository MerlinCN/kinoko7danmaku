"""主页面板 - 已登录界面"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
)

from .user_info_card import UserInfoCard
from .danmaku_control_card import DanmakuControlCard


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

        # 底部按钮区
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        button_layout.addStretch()

        self.logout_btn = QPushButton("退出登录")
        self.logout_btn.setFixedWidth(100)
        button_layout.addWidget(self.logout_btn)

        self.main_layout.addLayout(button_layout)
        self.main_layout.addStretch()

    def get_user_info_card(self) -> UserInfoCard:
        """获取用户信息卡片"""
        return self.user_info_card

    def get_danmaku_control_card(self) -> DanmakuControlCard:
        """获取弹幕控制卡片"""
        return self.danmaku_control_card

    def on_logout_clicked(self, callback) -> None:
        """设置退出登录按钮的回调"""
        self.logout_btn.clicked.connect(callback)
