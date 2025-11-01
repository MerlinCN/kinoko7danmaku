"""用户信息卡片组件"""

from pathlib import Path
import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
)
from qfluentwidgets import CardWidget, BodyLabel, CaptionLabel
from qasync import asyncSlot
from bilibili_api import user, Credential
from loguru import logger


class UserInfoCard(CardWidget):
    """用户信息卡片

    显示当前登录用户的基本信息（用户名、头像、房间号、粉丝数、等级等）
    """

    user_info_loaded = Signal(dict)

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
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(80, 80)
        self.avatar_label.setStyleSheet(
            "border: 1px solid #e1e1e1; border-radius: 40px; background: #f3f3f3;"
        )
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.avatar_label)

        # 用户信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)

        # 用户名
        self.name_label = BodyLabel("加载中...")
        info_layout.addWidget(self.name_label)

        # 房间号
        self.room_id_label = CaptionLabel("房间号: 加载中...")
        info_layout.addWidget(self.room_id_label)

        # 粉丝数
        self.follower_label = CaptionLabel("粉丝数: 加载中...")
        info_layout.addWidget(self.follower_label)

        # 等级
        self.level_label = CaptionLabel("等级: 加载中...")
        info_layout.addWidget(self.level_label)

        self.main_layout.addLayout(info_layout, 1)

        # 刷新按钮
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setFixedWidth(80)
        self.refresh_btn.clicked.connect(self._load_user_info)
        self.main_layout.addWidget(self.refresh_btn)

    @asyncSlot()
    async def _load_user_info(self) -> None:
        """加载用户信息"""
        try:
            # 从 cookies.json 加载凭据
            cookies_path = Path("cookies.json")
            if not cookies_path.exists():
                self.name_label.setText("未登录")
                return

            with open(cookies_path, "r", encoding="utf-8") as f:
                login_info = json.load(f)

            # 提取 cookie 信息
            cookies = login_info["cookie_info"]["cookies"]
            bili_jct = None
            sessdata = None
            dedeuserid = None

            for cookie in cookies:
                if cookie["name"] == "bili_jct":
                    bili_jct = cookie["value"]
                if cookie["name"] == "SESSDATA":
                    sessdata = cookie["value"]
                if cookie["name"] == "DedeUserID":
                    dedeuserid = cookie["value"]

            if not (bili_jct and sessdata and dedeuserid):
                logger.error("cookies 信息不完整")
                self.name_label.setText("登录信息错误")
                return

            credential = Credential(
                bili_jct=bili_jct,
                sessdata=sessdata,
                dedeuserid=dedeuserid,
            )

            # 获取当前用户信息
            self_info = await user.get_self_info(credential=credential)
            self.user_info = self_info

            # 获取用户的详细信息（包括粉丝数）
            u = user.User(uid=self_info["mid"], credential=credential)
            relation_info = await u.get_relation_info()
            self.relation_info = relation_info

            # 更新 UI
            self._update_ui()
            self.user_info_loaded.emit(self.user_info)

        except Exception as e:
            logger.error(f"加载用户信息失败: {e}")
            self.name_label.setText(f"加载失败: {str(e)}")

    def _update_ui(self) -> None:
        """更新 UI"""
        if not self.user_info:
            return

        # 更新用户名
        uname = self.user_info.get("uname", "未知用户")
        self.name_label.setText(uname)

        # 获取房间号（需要从设置中读取）
        try:
            from core import setting

            room_id = setting.bili_service.room_id
            self.room_id_label.setText(f"房间号: {room_id}")
        except Exception:
            self.room_id_label.setText("房间号: 未设置")

        # 更新粉丝数
        follower = self.relation_info.get("follower", 0)
        self.follower_label.setText(f"粉丝数: {follower:,}")

        # 更新等级
        level_info = self.user_info.get("level_info", {})
        level = level_info.get("current_level", 0)
        self.level_label.setText(f"等级: LV {level}")

        # 加载头像
        face_url = self.user_info.get("face", "")
        if face_url:
            self._load_avatar(face_url)

    @asyncSlot(str)
    async def _load_avatar(self, url: str) -> None:
        """加载头像"""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        pixmap = QPixmap()
                        pixmap.loadFromData(data)
                        # 缩放头像
                        scaled_pixmap = pixmap.scaledToWidth(
                            80, Qt.SmoothTransformation
                        )
                        self.avatar_label.setPixmap(scaled_pixmap)
        except Exception as e:
            logger.warning(f"加载头像失败: {e}")
