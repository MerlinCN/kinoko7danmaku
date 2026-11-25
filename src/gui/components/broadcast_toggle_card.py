"""播报开关卡片"""

from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CaptionLabel, CardWidget, ConfigItem, SubtitleLabel, SwitchButton, qconfig

from core.qconfig import cfg


class BroadcastToggleCard(CardWidget):
    """播报开关卡片

    提供弹幕、免费礼物、舰长、醒目留言的播报开关，并展示礼物合并窗口。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化播报开关卡片

        Args:
            parent: 父组件
        """
        super().__init__(parent)
        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(6)

        layout.addWidget(SubtitleLabel('播报开关', self))

        self._add_switch_row(layout, '弹幕播报', cfg.normalDanmakuOn)
        self._add_switch_row(layout, '免费礼物', cfg.freeGiftOn)
        self._add_switch_row(layout, '舰长播报', cfg.guardOn)
        self._add_switch_row(layout, '醒目留言', cfg.superChatOn)

        merge_layout = QHBoxLayout()
        merge_layout.setSpacing(8)
        merge_layout.addWidget(CaptionLabel('礼物合并窗口', self))
        merge_layout.addStretch()
        self.merge_window_label = BodyLabel(f'{cfg.giftMergeWindow.value:.1f}s', self)
        merge_layout.addWidget(self.merge_window_label)
        layout.addLayout(merge_layout)

    def _add_switch_row(self, layout: QVBoxLayout, title: str, item: ConfigItem) -> None:
        """添加一行开关

        Args:
            layout: 目标布局
            title: 开关名称
            item: 绑定的配置项
        """
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(BodyLabel(title, self))
        row.addStretch()

        switch = SwitchButton(self)
        switch.setOnText('')
        switch.setOffText('')
        switch.setChecked(bool(item.value))
        switch.checkedChanged.connect(lambda checked, config_item=item: qconfig.set(config_item, checked))
        item.valueChanged.connect(lambda value, target=switch: self._sync_switch(target, value))
        row.addWidget(switch)

        layout.addLayout(row)

    def _connect_signals(self) -> None:
        """连接配置变化信号"""
        cfg.giftMergeWindow.valueChanged.connect(self._on_merge_window_changed)

    def _sync_switch(self, switch: SwitchButton, value: object) -> None:
        """同步开关状态（不触发配置更新）

        Args:
            switch: 开关控件
            value: 配置值
        """
        with QSignalBlocker(switch):
            switch.setChecked(bool(value))

    def _on_merge_window_changed(self, value: object) -> None:
        """礼物合并窗口变化

        Args:
            value: 窗口秒数
        """
        self.merge_window_label.setText(f'{float(value):.1f}s')
