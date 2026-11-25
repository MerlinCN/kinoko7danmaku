"""主页面板 - 已登录界面"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget

from bilibili import bili_service
from models.bilibili import LiveMessage, SessionStats

from .audio_output_card import AudioOutputCard
from .broadcast_toggle_card import BroadcastToggleCard
from .message_feed import MessageFeed
from .room_header_card import RoomHeaderCard
from .stats_row import StatsRow
from .tts_summary_card import TtsSummaryCard


class HomePanel(QWidget):
    """主页面板

    已登录后的直播控制台：直播间头部、会话统计、实时消息流与右侧控制栏。
    """

    open_settings = Signal()
    open_audio_test = Signal()
    logout_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化主页面板

        Args:
            parent: 父组件
        """
        super().__init__(parent=parent)
        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        """初始化 UI"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(16)

        self.room_header_card = RoomHeaderCard(self)
        self.main_layout.addWidget(self.room_header_card)

        self.stats_row = StatsRow(self)
        self.main_layout.addWidget(self.stats_row)

        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(8)
        self.splitter.setStyleSheet('QSplitter::handle { background: transparent; }')

        self.message_feed = MessageFeed(self.splitter)
        self.message_feed.setMinimumWidth(460)

        side_panel = QWidget(self.splitter)
        side_panel.setMinimumWidth(300)
        side_layout = QVBoxLayout(side_panel)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(12)

        self.tts_card = TtsSummaryCard(side_panel)
        self.toggle_card = BroadcastToggleCard(side_panel)
        self.audio_card = AudioOutputCard(side_panel)
        side_layout.addWidget(self.tts_card)
        side_layout.addWidget(self.toggle_card)
        side_layout.addWidget(self.audio_card)
        side_layout.addStretch(1)

        self.splitter.addWidget(self.message_feed)
        self.splitter.addWidget(side_panel)
        self.splitter.setStretchFactor(0, 2)
        self.splitter.setStretchFactor(1, 1)

        self.main_layout.addWidget(self.splitter, 1)

    def _connect_signals(self) -> None:
        """连接服务与子组件信号"""
        bili_service.message_received.connect(self._on_message_received)
        bili_service.stats_changed.connect(self._on_stats_changed)
        bili_service.session_started.connect(self.message_feed.clear_messages)

        self.room_header_card.logout_requested.connect(self.logout_requested.emit)
        self.tts_card.open_settings.connect(self.open_settings.emit)
        self.audio_card.open_settings.connect(self.open_settings.emit)
        self.audio_card.open_audio_test.connect(self.open_audio_test.emit)

    def refresh(self) -> None:
        """刷新页面数据"""
        self.room_header_card.refresh()
        self.tts_card.refresh()
        self.audio_card.refresh()
        self.stats_row.update_stats(bili_service.stats)

    def _on_message_received(self, message: LiveMessage) -> None:
        """收到直播消息

        Args:
            message: 直播消息
        """
        self.message_feed.add_message(message)

    def _on_stats_changed(self, stats: SessionStats) -> None:
        """会话统计变化

        Args:
            stats: 会话统计
        """
        self.stats_row.update_stats(stats)
