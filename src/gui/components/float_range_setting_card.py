"""浮点数范围设置卡片"""

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QLabel, QWidget
from qfluentwidgets import FluentIconBase, SettingCard, Slider, qconfig
from qfluentwidgets.common.config import RangeConfigItem


class FloatRangeSettingCard(SettingCard):
    """支持浮点数和自定义步长的范围设置卡片

    滑块内部使用整数刻度，对外以浮点值交互：
    - 滑块刻度 = 浮点值 / step
    - 浮点值 = 滑块刻度 * step
    """

    valueChanged = Signal(float)

    def __init__(
        self,
        configItem: RangeConfigItem,
        icon: str | QIcon | FluentIconBase,
        title: str,
        content: str | None = None,
        step: float = 0.1,
        decimals: int = 1,
        parent: QWidget | None = None,
    ) -> None:
        """初始化浮点数范围设置卡片

        Args:
            configItem: 配置项
            icon: 图标
            title: 标题
            content: 描述
            step: 浮点步长（默认 0.1）
            decimals: 显示小数位数（默认 1）
            parent: 父组件
        """
        super().__init__(icon, title, content, parent)
        self.configItem = configItem
        self.step = step
        self.decimals = decimals

        self.slider = Slider(Qt.Orientation.Horizontal, self)
        self.valueLabel = QLabel(self)
        self.slider.setMinimumWidth(268)
        self.slider.setSingleStep(1)

        min_value, max_value = configItem.range
        self.slider.setRange(self._to_slider_value(min_value), self._to_slider_value(max_value))

        self.hBoxLayout.addStretch(1)
        self.hBoxLayout.addWidget(self.valueLabel, 0, Qt.AlignmentFlag.AlignRight)
        self.hBoxLayout.addSpacing(6)
        self.hBoxLayout.addWidget(self.slider, 0, Qt.AlignmentFlag.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self.valueLabel.setObjectName('valueLabel')
        self._update_label(configItem.value)
        self._update_slider(configItem.value)

        self.slider.valueChanged.connect(self._on_slider_value_changed)
        configItem.valueChanged.connect(self.setValue)

    def _to_slider_value(self, value: float) -> int:
        """将浮点值转换为滑块刻度

        Args:
            value: 浮点值

        Returns:
            int: 滑块刻度
        """
        return round(value / self.step)

    def _to_float_value(self, slider_value: int) -> float:
        """将滑块刻度转换为浮点值

        Args:
            slider_value: 滑块刻度

        Returns:
            float: 浮点值
        """
        return round(slider_value * self.step, self.decimals)

    def _on_slider_value_changed(self, slider_value: int) -> None:
        """滑块变化时同步配置项并向外发出浮点值

        Args:
            slider_value: 滑块刻度
        """
        value = self._to_float_value(slider_value)
        self.setValue(value)
        self.valueChanged.emit(value)

    def _update_slider(self, value: float) -> None:
        """将浮点值同步到滑块（不触发信号）

        Args:
            value: 浮点值
        """
        slider_value = self._to_slider_value(value)
        if slider_value == self.slider.value():
            return

        # QSignalBlocker 在作用域结束时自动恢复信号
        with QSignalBlocker(self.slider):
            self.slider.setValue(slider_value)

    def _update_label(self, value: float) -> None:
        """更新数值标签

        Args:
            value: 浮点值
        """
        self.valueLabel.setText(f'{value:.{self.decimals}f}')
        self.valueLabel.adjustSize()

    def setValue(self, value: float) -> None:
        """设置值（同时更新配置项、标签与滑块）

        Args:
            value: 浮点值
        """
        qconfig.set(self.configItem, value)

        # 配置项会按范围校验，以校验后的值刷新界面
        value = self.configItem.value
        self._update_label(value)
        self._update_slider(value)
