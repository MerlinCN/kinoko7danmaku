"""只读信息展示卡片"""

from collections.abc import Callable
from typing import Any, Union

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from qfluentwidgets import (
    BodyLabel,
    ConfigItem,
    FluentIconBase,
    SettingCard,
)

EMPTY_TEXT = "（未设置）"


def default_formatter(value: Any) -> str:
    """默认格式化器：bool 转开关，空字符串转占位符，其余转字符串

    Args:
        value: 任意类型的配置值

    Returns:
        str: 用于展示的文本
    """
    if isinstance(value, bool):
        return "开" if value else "关"
    if value is None or value == "":
        return EMPTY_TEXT
    return str(value)


def mask_secret(value: str) -> str:
    """对敏感字符串做掩码：保留前 4 与后 4 位，其余以 *** 替换

    Args:
        value: 原始字符串

    Returns:
        str: 掩码后的字符串；空字符串返回占位符；长度不足 8 时整体替换为 ***
    """
    if not value:
        return EMPTY_TEXT
    if len(value) < 8:
        return "***"
    return f"{value[:4]}***{value[-4:]}"


class ReadOnlyInfoCard(SettingCard):
    """只读信息展示卡片

    右侧以灰色不可变文本展示配置项的当前值，自动跟随 configItem.valueChanged 刷新。
    """

    def __init__(
        self,
        configItem: ConfigItem,
        icon: Union[str, QIcon, FluentIconBase],
        title: str,
        content: str | None = None,
        formatter: Callable[[Any], str] | None = None,
        mask: bool = False,
        parent=None,
    ) -> None:
        """初始化只读信息卡片

        Args:
            configItem: 要展示的配置项
            icon: 左侧图标
            title: 标题
            content: 描述文本
            formatter: 自定义值格式化器，None 时使用 default_formatter
            mask: 是否对值做敏感信息掩码（在 formatter 之前应用）
            parent: 父组件
        """
        super().__init__(icon, title, content, parent)
        self.configItem = configItem
        self._formatter = formatter or default_formatter
        self._mask = mask

        self.valueLabel = BodyLabel(self)
        self.valueLabel.setEnabled(False)
        self.valueLabel.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        self.hBoxLayout.addWidget(self.valueLabel, 0, Qt.AlignmentFlag.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self.refresh()
        configItem.valueChanged.connect(self.refresh)

    def refresh(self, *_: Any) -> None:
        """根据当前 configItem 值刷新展示文本"""
        value = self.configItem.value
        if self._mask:
            text = mask_secret(value if isinstance(value, str) else str(value))
        else:
            text = self._formatter(value)
        self.valueLabel.setText(text)
