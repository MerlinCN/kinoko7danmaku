"""直播间信息头部卡片"""

import aiohttp

from PySide6.QtCore import QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QToolButton, QVBoxLayout, QWidget
from bilibili_api import live
from loguru import logger
from qasync import asyncSlot
from qfluentwidgets import (
    Action,
    AvatarWidget,
    BodyLabel,
    CaptionLabel,
    CardWidget,
    PrimaryPushButton,
    PushButton,
    RoundMenu,
    SubtitleLabel,
    TransparentToolButton,
)
from qfluentwidgets import (
    FluentIcon as FIF,
)

from bilibili import bili_service
from core.qconfig import cfg
from gui.components.status_pill import StatusPill
from models.bilibili import ConnectionState, RoomSummary


class RoomHeaderCard(CardWidget):
    """直播间头部卡片

    展示主播、直播间状态、账号信息与连接控制。
    """

    logout_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化直播间头部卡片

        Args:
            parent: 父组件
        """
        super().__init__(parent)
        self._meta_text = f'房间 {cfg.roomId.value} · 在线 -- · --'
        self._account_text = '登录账号: --'

        self._init_ui()
        self._connect_signals()

        bili_service.connection_state_changed.connect(self._on_connection_state)
        cfg.roomId.valueChanged.connect(self._on_room_id_changed)
        self._on_connection_state(bili_service.connection_state.value)

        # 等待 Qt 事件循环启动后再创建定时器
        QTimer.singleShot(0, self._start_timer)

    def _init_ui(self) -> None:
        """初始化 UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        self.avatar_widget = AvatarWidget(self)
        self.avatar_widget.setRadius(28)
        self.avatar_widget.setFixedSize(56, 56)
        layout.addWidget(self.avatar_widget, 0, Qt.AlignmentFlag.AlignVCenter)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)
        self.anchor_label = SubtitleLabel('加载中...', self)
        self.live_pill = StatusPill(self)
        self.live_pill.set_status('未开播', '#8a8a8a')
        title_layout.addWidget(self.anchor_label)
        title_layout.addWidget(self.live_pill)
        title_layout.addStretch()

        self.room_title_label = BodyLabel('', self)
        self.meta_label = CaptionLabel(self._meta_text, self)

        info_layout.addLayout(title_layout)
        info_layout.addWidget(self.room_title_label)
        info_layout.addWidget(self.meta_label)
        layout.addLayout(info_layout, 1)

        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)

        self.connection_pill = StatusPill(self)
        action_layout.addWidget(self.connection_pill, 0, Qt.AlignmentFlag.AlignVCenter)

        self.open_btn = PushButton('打开直播间', self)
        self.open_btn.setIcon(FIF.LINK)
        action_layout.addWidget(self.open_btn)

        self.start_btn = PrimaryPushButton('开始监听', self)
        self.start_btn.setIcon(FIF.PLAY)
        action_layout.addWidget(self.start_btn)

        self.stop_btn = PushButton('停止监听', self)
        self.stop_btn.setIcon(FIF.PAUSE)
        self.stop_btn.setEnabled(False)
        action_layout.addWidget(self.stop_btn)

        self.more_btn = TransparentToolButton(FIF.MORE, self)
        self.more_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        action_layout.addWidget(self.more_btn)

        layout.addLayout(action_layout)

        self._init_menu()

    def _init_menu(self) -> None:
        """初始化更多操作菜单"""
        menu = RoundMenu(parent=self)
        menu.addAction(Action(FIF.SYNC, '刷新房间信息', triggered=self._on_refresh_room_action))
        menu.addAction(Action(FIF.PEOPLE, '刷新账号信息', triggered=self._on_refresh_self_action))
        menu.addSeparator()
        menu.addAction(Action(FIF.CLOSE, '退出登录', triggered=self._on_logout_action))
        self.more_btn.setMenu(menu)

    def _connect_signals(self) -> None:
        """连接按钮信号"""
        self.open_btn.clicked.connect(self._open_room)
        self.start_btn.clicked.connect(self._on_start_clicked)
        self.stop_btn.clicked.connect(self._on_stop_clicked)

    def _start_timer(self) -> None:
        """启动房间信息定时刷新"""
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_room_info)
        self.refresh_timer.setInterval(60_000)
        self.refresh_timer.start()
        self.refresh()

    def refresh(self) -> None:
        """刷新房间与账号信息"""
        self._refresh_room_info()
        self._refresh_self_info()

    @asyncSlot()
    async def _refresh_room_info(self) -> None:
        """刷新直播间信息"""
        room_id = cfg.roomId.value
        self._meta_text = f'房间 {room_id} · 在线 -- · --'
        self._update_meta()

        if not bili_service.credential:
            self._apply_placeholder(room_id)
            return

        try:
            room = live.LiveRoom(room_id, credential=bili_service.credential)
            data = await room.get_room_info()
            summary = RoomSummary.from_api(data)
        except Exception as e:
            logger.warning(f'获取直播间信息失败: {e}')
            self._apply_placeholder(room_id)
            return

        self._apply_room(summary)

    @asyncSlot()
    async def _refresh_self_info(self) -> None:
        """刷新登录账号信息"""
        if not bili_service.credential:
            self._account_text = '登录账号: --'
            self._update_meta()
            return

        try:
            info = await bili_service.get_self_info()
        except Exception as e:
            logger.warning(f'获取账号信息失败: {e}')
            self._account_text = '登录账号: 获取失败'
            self._update_meta()
            return

        self._account_text = f'登录账号: {info.uname} (UID {info.mid})'
        self._update_meta()

    def _apply_room(self, summary: RoomSummary) -> None:
        """应用直播间信息

        Args:
            summary: 直播间概要
        """
        self.anchor_label.setText(summary.uname)
        self.room_title_label.setText(summary.title or '未设置标题')
        self.room_title_label.setToolTip(summary.title)
        self.live_pill.set_status(summary.live_text, summary.live_color)
        self._meta_text = f'房间 {summary.room_id} · 在线 {summary.online:,} · {summary.area_name or "未知分区"}'
        self._update_meta()

        if summary.face:
            self._load_avatar(summary.face)

    def _apply_placeholder(self, room_id: int) -> None:
        """应用占位信息

        Args:
            room_id: 房间号
        """
        self.room_title_label.setText('获取直播间信息失败')
        self.room_title_label.setToolTip('')
        self.live_pill.set_status('未知', '#8a8a8a')
        self._meta_text = f'房间 {room_id} · 在线 -- · --'
        self._update_meta()

    def _update_meta(self) -> None:
        """更新概要信息标签"""
        self.meta_label.setText(f'{self._meta_text} · {self._account_text}')

    @asyncSlot(str)
    async def _load_avatar(self, url: str) -> None:
        """加载主播头像

        Args:
            url: 头像 URL
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return
                    data = await resp.read()
        except Exception as e:
            logger.warning(f'加载直播间头像失败: {e}')
            return

        pixmap = QPixmap()
        pixmap.loadFromData(data)
        self.avatar_widget.setImage(pixmap)

    @asyncSlot()
    async def _on_start_clicked(self) -> None:
        """开始监听"""
        await bili_service.run()

    @asyncSlot()
    async def _on_stop_clicked(self) -> None:
        """停止监听"""
        await bili_service.stop()

    def _open_room(self) -> None:
        """打开直播间网页"""
        QDesktopServices.openUrl(QUrl(f'https://live.bilibili.com/{cfg.roomId.value}'))

    def _on_connection_state(self, state_value: str) -> None:
        """连接状态变化

        Args:
            state_value: 连接状态值
        """
        state = ConnectionState(state_value)
        self.connection_pill.set_state(state)

        active = state in (ConnectionState.CONNECTING, ConnectionState.CONNECTED)
        self.start_btn.setEnabled(not active)
        self.stop_btn.setEnabled(active)
        self.start_btn.setText('连接中...' if state == ConnectionState.CONNECTING else '开始监听')

    def _on_room_id_changed(self, _value: object) -> None:
        """房间号变化"""
        self._refresh_room_info()

    def _on_refresh_room_action(self, _checked: bool = False) -> None:
        """菜单：刷新房间信息"""
        self._refresh_room_info()

    def _on_refresh_self_action(self, _checked: bool = False) -> None:
        """菜单：刷新账号信息"""
        self._refresh_self_info()

    def _on_logout_action(self, _checked: bool = False) -> None:
        """菜单：退出登录"""
        self.logout_requested.emit()
