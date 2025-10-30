"""整数输入设置卡片"""

from typing import Union

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QIntValidator
from qfluentwidgets import ConfigItem, FluentIconBase, LineEdit, SettingCard, qconfig


class IntSettingCard(SettingCard):
    """带整数输入框的设置卡片

    用于整数输入的设置卡片，直接绑定到 ConfigItem。
    """

    valueChanged = Signal(int)

    def __init__(
        self,
        configItem: ConfigItem,
        icon: Union[str, QIcon, FluentIconBase],
        title: str,
        content: str | None = None,
        parent=None,
        placeholder: str = "",
    ) -> None:
        """初始化整数输入设置卡片

        Args:
            configItem: 配置项
            icon: 图标
            title: 标题
            content: 描述内容
            parent: 父组件
        """
        super().__init__(icon, title, content, parent)
        self.configItem = configItem
        self.lineEdit = LineEdit(self)
        if placeholder:
            self.lineEdit.setPlaceholderText(placeholder)
        # 设置整数验证器
        validator = QIntValidator(self)

        validator.setBottom(0)
        self.lineEdit.setValidator(validator)

        # 设置当前值
        self.lineEdit.setText(str(configItem.value))

        # 设置输入框宽度
        self.lineEdit.setFixedWidth(200)

        # 添加到布局
        self.hBoxLayout.addStretch(1)
        self.hBoxLayout.addWidget(self.lineEdit, 0, Qt.AlignmentFlag.AlignRight)
        self.hBoxLayout.addSpacing(16)

        # 连接信号
        configItem.valueChanged.connect(self.setValue)
        self.lineEdit.textChanged.connect(self._on_text_changed)

    def _on_text_changed(self, text: str) -> None:
        """输入框文本改变时的回调"""
        if text and text.isdigit():
            value = int(text)
            self.setValue(value)
            self.valueChanged.emit(value)

    def setValue(self, value: int) -> None:
        """设置值

        Args:
            value: 新值
        """
        qconfig.set(self.configItem, value)
        self.lineEdit.setText(str(value))
