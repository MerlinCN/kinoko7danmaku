"""字符串输入设置卡片"""

from typing import Union

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from qfluentwidgets import (
    ConfigItem,
    FluentIconBase,
    LineEdit,
    SettingCard,
    ToolButton,
    qconfig,
)
from qfluentwidgets import (
    FluentIcon as FIF,
)


class StrSettingCard(SettingCard):
    """带文本输入框的设置卡片

    用于字符串输入的设置卡片，直接绑定到 ConfigItem。
    """

    valueChanged = Signal(str)
    refreshRequested = Signal()  # 刷新按钮点击信号

    def __init__(
        self,
        configItem: ConfigItem,
        icon: Union[str, QIcon, FluentIconBase],
        title: str,
        content: str | None = None,
        parent=None,
        placeholder: str = "",
        refreshable: bool = False,
    ) -> None:
        """初始化字符串输入设置卡片

        Args:
            configItem: 配置项
            icon: 图标
            title: 标题
            content: 描述内容
            parent: 父组件
            placeholder: 占位符文本
            refreshable: 是否可刷新
        """
        super().__init__(icon, title, content, parent)
        self.configItem = configItem
        self.lineEdit = LineEdit(self)

        # 设置当前值
        self.lineEdit.setText(str(configItem.value))

        # 设置占位符
        if placeholder:
            self.lineEdit.setPlaceholderText(placeholder)

        # 设置输入框宽度
        self.lineEdit.setFixedWidth(300)

        # 添加到布局
        self.hBoxLayout.addStretch(1)
        self.hBoxLayout.addWidget(self.lineEdit, 0, Qt.AlignmentFlag.AlignRight)
        if refreshable:
            self.refresh_btn = ToolButton(FIF.SYNC, self)
            self.hBoxLayout.addSpacing(8)  # 输入框和按钮之间的间隔
            self.hBoxLayout.addWidget(self.refresh_btn, 0, Qt.AlignmentFlag.AlignRight)
            self.refresh_btn.clicked.connect(self.refreshRequested.emit)
        self.hBoxLayout.addSpacing(16)

        # 连接信号
        configItem.valueChanged.connect(self.setValue)
        self.lineEdit.textChanged.connect(self._on_text_changed)

    def _on_text_changed(self, text: str) -> None:
        """输入框文本改变时的回调"""
        self.setValue(text)
        self.valueChanged.emit(text)

    def setValue(self, value: str) -> None:
        """设置值

        Args:
            value: 新值
        """
        qconfig.set(self.configItem, value)
        self.lineEdit.setText(value)
