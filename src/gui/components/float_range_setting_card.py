"""浮点数范围设置卡片"""

from typing import Union

from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon
from qfluentwidgets import RangeSettingCard, qconfig
from qfluentwidgets.common.config import RangeConfigItem
from qfluentwidgets.common.icon import FluentIconBase


class FloatRangeSettingCard(RangeSettingCard):
    """支持浮点数和自定义步长的范围设置卡片

    相比 RangeSettingCard，支持：
    - 浮点数值
    - 自定义步长
    - 自定义显示精度
    """

    valueChanged = Signal(float)

    def __init__(
        self,
        configItem: RangeConfigItem,
        icon: Union[str, QIcon, FluentIconBase],
        title: str,
        content: str | None = None,
        step: float = 0.1,
        decimals: int = 1,
        parent=None,
    ) -> None:
        """初始化浮点数范围设置卡片

        Args:
            configItem: 配置项
            icon: 图标
            title: 标题
            content: 描述
            step: 步长（默认 0.1）
            decimals: 显示小数位数（默认 1）
            parent: 父组件
        """
        self.step = step
        self.decimals = decimals
        self._internal_step = int(1 / step)  # 内部步长倍数

        # 调用父类初始化（会设置 slider）
        super().__init__(configItem, icon, title, content, parent)

        # 重新配置 slider 以支持浮点数
        self._reconfigure_slider()

    def _reconfigure_slider(self) -> None:
        """重新配置滑块以支持浮点数"""
        min_val, max_val = self.configItem.range

        # 将浮点数范围转换为整数范围
        self.slider.setRange(
            int(min_val * self._internal_step), int(max_val * self._internal_step)
        )
        self.slider.setSingleStep(1)  # 内部步长始终为 1
        self.slider.setValue(int(self.configItem.value * self._internal_step))

        # 更新显示标签
        self._update_label(self.configItem.value)

    def _update_label(self, value: float) -> None:
        """更新显示标签

        Args:
            value: 要显示的浮点数值
        """
        self.valueLabel.setText(f"{value:.{self.decimals}f}")
        self.valueLabel.adjustSize()

    def _RangeSettingCard__onValueChanged(self, internal_value: int) -> None:
        """滑块值变化槽函数（重写父类方法）

        Args:
            internal_value: 内部整数值
        """
        # 转换为浮点数
        float_value = internal_value / self._internal_step

        # 四舍五入到指定精度
        float_value = round(float_value, self.decimals)

        # 更新配置
        qconfig.set(self.configItem, float_value)

        # 更新显示
        self._update_label(float_value)

        # 发送信号
        self.valueChanged.emit(float_value)

    def setValue(self, value: float) -> None:
        """设置滑块值

        Args:
            value: 浮点数值
        """
        # 更新配置
        qconfig.set(self.configItem, value)

        # 更新滑块
        internal_value = int(value * self._internal_step)
        self.slider.setValue(internal_value)

        # 更新显示
        self._update_label(value)
