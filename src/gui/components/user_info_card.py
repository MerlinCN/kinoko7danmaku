"""用户信息卡片组件"""

import aiohttp
from loguru import logger
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)
from qasync import asyncSlot
from qfluentwidgets import (
    AvatarWidget,
    CaptionLabel,
    CardWidget,
    PushButton,
)

from bilibili import bili_service


class UserInfoCard(CardWidget):
    """用户信息卡片

    显示当前登录用户的基本信息（用户名、头像、房间号、粉丝数、等级等）
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.user_info = {}
        self.relation_info = {}
        self._init_ui()
        self._load_user_info()

    def _init_ui(self) -> None:
        """初始化 UI"""
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setSpacing(16)
        self.main_layout.setContentsMargins(20, 20, 20, 20)

        # 头像
        self.avatar_label = AvatarWidget()
        self.avatar_label.setRadius(40)
        self.main_layout.addWidget(self.avatar_label)

        # 用户信息
        info_layout = QVBoxLayout()

        # 用户名
        self.name_label = CaptionLabel("用户名: 加载中...")
        info_layout.addWidget(self.name_label)

        # 房间号
        self.uid_label = CaptionLabel("UID: 加载中...")
        info_layout.addWidget(self.uid_label)

        # 粉丝数
        self.follower_label = CaptionLabel("粉丝数: 加载中...")
        info_layout.addWidget(self.follower_label)

        self.main_layout.addLayout(info_layout, 1)

        # 按钮区域
        button_layout = QVBoxLayout()
        button_layout.setSpacing(8)

        # 刷新按钮
        self.refresh_btn = PushButton("刷新")
        self.refresh_btn.setFixedWidth(80)
        self.refresh_btn.clicked.connect(self._load_user_info)
        button_layout.addWidget(self.refresh_btn)

        # 退出登录按钮
        self.logout_btn = PushButton("退出登录")
        self.logout_btn.setFixedWidth(80)
        self.logout_btn.clicked.connect(self._on_logout)
        button_layout.addWidget(self.logout_btn)

        self.main_layout.addLayout(button_layout)

    @asyncSlot()
    async def _load_user_info(self) -> None:
        """加载用户信息"""
        if not bili_service.credential:
            return
        try:
            self_info = await bili_service.get_self_info()
            self.user_info = self_info

            # 更新 UI
            self._update_ui()

        except Exception as e:
            logger.error(f"加载用户信息失败: {e}")
            self.name_label.setText(f"加载失败: {str(e)}")

    def _update_ui(self) -> None:
        """更新 UI"""
        if not self.user_info:
            return

        # 更新用户名
        uname = self.user_info.get("name", "未知用户")
        self.name_label.setText(f"用户名: {uname}")

        # 获取UID
        uid = self.user_info.get("mid", 0)
        self.uid_label.setText(f"UID: {uid}")

        # 更新粉丝数
        follower = self.user_info.get("follower", 0)
        self.follower_label.setText(f"粉丝数: {follower:,}")
        # 加载头像
        face_url = self.user_info.get("face", "")
        if face_url:
            self._load_avatar(face_url)

    @asyncSlot(str)
    async def _load_avatar(self, url: str) -> None:
        """加载头像"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        pixmap = QPixmap()
                        pixmap.loadFromData(data)
                        self.avatar_label.setImage(pixmap)
        except Exception as e:
            logger.warning(f"加载头像失败: {e}")

    @asyncSlot()
    async def _on_logout(self) -> None:
        """退出登录"""
        await bili_service.logout()
