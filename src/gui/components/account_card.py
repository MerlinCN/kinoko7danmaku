"""登录账号卡片"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from loguru import logger
from qasync import asyncSlot
from qfluentwidgets import AvatarWidget, BodyLabel, CaptionLabel, CardWidget, PushButton, SubtitleLabel

from bilibili import bili_service
from gui.components.avatar import load_avatar_pixmap
from models.bilibili import SelfInfo


class AccountCard(CardWidget):
    """登录账号卡片

    展示当前登录账号的头像、昵称与 UID，并提供退出登录入口。
    """

    logout_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化登录账号卡片

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

        header_layout = QHBoxLayout()
        header_layout.addWidget(SubtitleLabel('登录账号', self))
        header_layout.addStretch()

        self.logout_btn = PushButton('退出登录', self)
        self.logout_btn.clicked.connect(self._on_logout)
        header_layout.addWidget(self.logout_btn)
        layout.addLayout(header_layout)

        body_layout = QHBoxLayout()
        body_layout.setSpacing(12)

        self.avatar_widget = AvatarWidget(self)
        self.avatar_widget.setRadius(18)
        self.avatar_widget.setFixedSize(36, 36)
        body_layout.addWidget(self.avatar_widget, 0, Qt.AlignmentFlag.AlignVCenter)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(0)
        self.name_label = BodyLabel('--', self)
        self.uid_label = CaptionLabel('UID --', self)
        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.uid_label)
        body_layout.addLayout(info_layout, 1)

        layout.addLayout(body_layout)

    def refresh(self) -> None:
        """刷新账号信息"""
        self._refresh_self_info()

    @asyncSlot()
    async def _refresh_self_info(self) -> None:
        """拉取当前登录账号信息"""
        if not bili_service.credential:
            self._apply_placeholder()
            return

        try:
            info = await bili_service.get_self_info()
        except Exception as e:
            logger.warning(f'获取账号信息失败: {e!r}')
            self._apply_placeholder()
            return

        self._apply_info(info)

    def _apply_info(self, info: SelfInfo) -> None:
        """应用账号信息

        Args:
            info: 账号信息
        """
        self.name_label.setText(info.uname or '未知账号')
        self.uid_label.setText(f'UID {info.mid}')
        if info.face:
            self._load_avatar(info.face)

    def _apply_placeholder(self) -> None:
        """应用未登录占位信息"""
        self.name_label.setText('--')
        self.uid_label.setText('UID --')

    @asyncSlot(str)
    async def _load_avatar(self, url: str) -> None:
        """加载账号头像

        Args:
            url: 头像地址
        """
        pixmap = await load_avatar_pixmap(url)
        if pixmap is not None:
            self.avatar_widget.setImage(pixmap)

    def _on_logout(self, _checked: bool = False) -> None:
        """退出登录"""
        self.logout_requested.emit()

    def showEvent(self, event: QShowEvent) -> None:
        """页面显示时刷新账号信息"""
        super().showEvent(event)
        self.refresh()
