"""实时消息流组件"""

from collections import deque
from datetime import UTC, datetime

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    ScrollArea,
    SegmentedWidget,
    SubtitleLabel,
    TransparentToolButton,
)
from qfluentwidgets import (
    FluentIcon as FIF,
)

from models.bilibili import LiveMessage, LiveMessageType

_MAX_MESSAGES = 300

_BADGE_STYLES: dict[LiveMessageType, tuple[str, str]] = {
    LiveMessageType.DANMAKU: ('弹幕', '#3b82f6'),
    LiveMessageType.GIFT: ('礼物', '#e8792b'),
    LiveMessageType.GUARD: ('舰长', '#8b5cf6'),
    LiveMessageType.SUPER_CHAT: ('SC', '#b8860b'),
}


class MessageRow(QWidget):
    """单条实时消息"""

    def __init__(self, message: LiveMessage, parent: QWidget | None = None) -> None:
        """初始化消息行

        Args:
            message: 直播消息
            parent: 父组件
        """
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)

        badge_text, badge_color = _BADGE_STYLES[message.type]
        badge = BodyLabel(badge_text, self)
        badge.setFixedWidth(40)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(f'color: white; background: {badge_color}; border-radius: 4px;')

        time_label = CaptionLabel(
            datetime.fromtimestamp(message.timestamp, tz=UTC).astimezone().strftime('%H:%M:%S'), self
        )

        text_label = BodyLabel(message.text, self)
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(time_label, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(text_label, 1)


class MessageFeed(CardWidget):
    """实时消息流

    按类型展示弹幕、礼物、舰长与醒目留言，支持过滤、暂停滚动与清空。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化消息流

        Args:
            parent: 父组件
        """
        super().__init__(parent)
        self._messages: deque[LiveMessage] = deque(maxlen=_MAX_MESSAGES)
        self._rows: list[MessageRow] = []
        self._filter: LiveMessageType | None = None
        self._paused = False

        self._init_ui()

    def _init_ui(self) -> None:
        """初始化 UI"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 16, 20, 16)
        self.main_layout.setSpacing(12)

        # 标题栏
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        self.title_label = SubtitleLabel('实时消息', self)
        header_layout.addWidget(self.title_label)

        self.filter_segmented = SegmentedWidget(self)
        self.filter_segmented.addItem('all', '全部')
        self.filter_segmented.addItem(LiveMessageType.DANMAKU.value, '弹幕')
        self.filter_segmented.addItem(LiveMessageType.GIFT.value, '礼物')
        self.filter_segmented.addItem(LiveMessageType.GUARD.value, '舰长')
        self.filter_segmented.addItem(LiveMessageType.SUPER_CHAT.value, 'SC')
        self.filter_segmented.setCurrentItem('all')
        self.filter_segmented.currentItemChanged.connect(self._on_filter_changed)
        header_layout.addWidget(self.filter_segmented)

        header_layout.addStretch()

        self.pause_btn = TransparentToolButton(FIF.PAUSE, self)
        self.pause_btn.setCheckable(True)
        self.pause_btn.setToolTip('暂停自动滚动')
        self.pause_btn.toggled.connect(self._on_pause_toggled)
        header_layout.addWidget(self.pause_btn)

        self.clear_btn = TransparentToolButton(FIF.BROOM, self)
        self.clear_btn.setToolTip('清空消息')
        self.clear_btn.clicked.connect(self.clear_messages)
        header_layout.addWidget(self.clear_btn)

        self.main_layout.addLayout(header_layout)

        # 消息滚动区
        self.scroll_area = ScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.enableTransparentBackground()
        self.scroll_area.setMinimumHeight(240)

        self._container = QWidget()
        self.rows_layout = QVBoxLayout(self._container)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(6)

        self.empty_label = BodyLabel('暂无消息', self._container)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rows_layout.addWidget(self.empty_label)
        self.rows_layout.addStretch(1)

        self.scroll_area.setWidget(self._container)
        self.main_layout.addWidget(self.scroll_area, 1)

    def add_message(self, message: LiveMessage) -> None:
        """添加一条消息

        Args:
            message: 直播消息
        """
        self._messages.append(message)
        if not self._matches(message):
            return

        self._append_row(message)
        if not self._paused:
            QTimer.singleShot(0, self._scroll_to_bottom)

    def clear_messages(self) -> None:
        """清空所有消息"""
        self._messages.clear()
        self._clear_rows()

    def _matches(self, message: LiveMessage) -> bool:
        """判断消息是否匹配当前过滤条件

        Args:
            message: 直播消息

        Returns:
            bool: 是否显示
        """
        return self._filter is None or message.type == self._filter

    def _append_row(self, message: LiveMessage) -> None:
        """追加一行消息

        Args:
            message: 直播消息
        """
        row = MessageRow(message, self._container)
        self.rows_layout.insertWidget(self.rows_layout.count() - 1, row)
        self._rows.append(row)
        self.empty_label.setVisible(False)

        if len(self._rows) > _MAX_MESSAGES:
            self._rows.pop(0).deleteLater()

    def _clear_rows(self) -> None:
        """清空所有消息行"""
        for row in self._rows:
            self.rows_layout.removeWidget(row)
            row.deleteLater()
        self._rows.clear()
        self.empty_label.setVisible(True)

    def _rebuild(self) -> None:
        """按当前过滤条件重建消息行"""
        self._clear_rows()
        for message in self._messages:
            if self._matches(message):
                self._append_row(message)
        if self._rows:
            self.empty_label.setVisible(False)
        self._scroll_to_bottom()

    def _on_filter_changed(self, route_key: str) -> None:
        """过滤条件变化

        Args:
            route_key: 分段控件路由键
        """
        self._filter = None if route_key == 'all' else LiveMessageType(route_key)
        self._rebuild()

    def _on_pause_toggled(self, checked: bool) -> None:
        """暂停/恢复自动滚动

        Args:
            checked: 是否暂停
        """
        self._paused = checked
        self.pause_btn.setIcon(FIF.PLAY if checked else FIF.PAUSE)
        self.pause_btn.setToolTip('恢复自动滚动' if checked else '暂停自动滚动')
        if not checked:
            self._scroll_to_bottom()

    def _scroll_to_bottom(self) -> None:
        """滚动到底部"""
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
