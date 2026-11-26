"""MiniMax 页面视觉组件

提供落地页风格的主视觉卡片、指标卡片与步骤标题。
"""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPaintEvent, QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CaptionLabel, CardWidget, TitleLabel
from qfluentwidgets.common.font import getFont

ACCENT = '#e73562'
ACCENT_SOFT = 'rgba(231, 53, 98, 38)'
INK = '#181e25'
INK_END = '#242c35'


def accent_button_qss(accent: str = ACCENT) -> str:
    """主视觉卡片内的强调色按钮样式

    Args:
        accent: 按钮底色

    Returns:
        QSS 字符串，浅色与深色主题通用
    """
    return (
        f'PushButton{{background:{accent};color:white;border:none;border-radius:6px;padding:6px 18px;}}'
        'PushButton:hover{background:rgba(255, 255, 255, 26);}'
        'PushButton:pressed{background:rgba(0, 0, 0, 40);}'
    )


def ghost_button_qss() -> str:
    """主视觉卡片内的描边按钮样式

    Returns:
        QSS 字符串，浅色与深色主题通用
    """
    return (
        'PushButton{background:transparent;color:white;border:1px solid rgba(255,255,255,90);'
        'border-radius:6px;padding:6px 18px;}'
        'PushButton:hover{background:rgba(255,255,255,20);}'
        'PushButton:pressed{background:rgba(255,255,255,10);}'
    )


class HeroCard(QWidget):
    """落地页风格的主视觉卡片

    深色渐变背景，包含标签、大标题、副文案与操作按钮区域。
    """

    def __init__(
        self,
        tag: str,
        title: str,
        slogan: str,
        parent: QWidget | None = None,
        accent: str = ACCENT,
    ) -> None:
        """初始化主视觉卡片

        Args:
            tag: 左上角标签文案
            title: 大标题
            slogan: 副文案
            parent: 父组件
            accent: 强调色
        """
        super().__init__(parent)
        self.setFixedHeight(178)
        self.accent = accent

        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 22, 34, 22)
        layout.setSpacing(8)

        self.tag_label = QLabel(tag, self)
        self.tag_label.setFont(getFont(11, QFont.Weight.DemiBold))
        self.tag_label.setStyleSheet(f'color: white; background: {accent}; border-radius: 9px; padding: 1px 10px;')
        layout.addWidget(self.tag_label, 0, Qt.AlignmentFlag.AlignLeft)

        self.title_label = QLabel(title, self)
        self.title_label.setFont(getFont(30, QFont.Weight.Black))
        self.title_label.setStyleSheet('color: white;')
        layout.addWidget(self.title_label)

        self.slogan_label = QLabel(slogan, self)
        self.slogan_label.setFont(getFont(13))
        self.slogan_label.setStyleSheet('color: rgba(255, 255, 255, 175);')
        layout.addWidget(self.slogan_label)

        self.action_layout = QHBoxLayout()
        self.action_layout.setSpacing(10)
        self.action_layout.addStretch(1)
        layout.addLayout(self.action_layout)

    def add_action(self, widget: QWidget) -> None:
        """在操作区追加一个按钮

        Args:
            widget: 按钮组件
        """
        self.action_layout.insertWidget(self.action_layout.count() - 1, widget)

    def paintEvent(self, _event: QPaintEvent) -> None:
        """绘制深色渐变背景、左侧强调条与右侧声波装饰

        Args:
            _event: 绘制事件
        """
        painter = QPainter(self)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing)

        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor(INK))
        gradient.setColorAt(1, QColor(INK_END))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(self.rect(), 12, 12)

        painter.setBrush(QColor(self.accent))
        painter.drawRoundedRect(QRectF(0, 30, 4, 44), 2, 2)

        self._draw_wave(painter)
        painter.end()

    def _draw_wave(self, painter: QPainter) -> None:
        """在右侧绘制声波装饰

        Args:
            painter: 绘制器
        """
        heights = [26, 46, 68, 42, 76, 54, 34, 60, 28]
        bar_width = 6
        gap = 10
        center_y = self.height() / 2
        start_x = self.width() - 34 - len(heights) * (bar_width + gap) + gap

        for index, height in enumerate(heights):
            color = QColor(self.accent) if index % 2 == 0 else QColor(255, 255, 255)
            color.setAlpha(110 if index % 2 == 0 else 40)
            painter.setBrush(color)
            rect = QRectF(start_x + index * (bar_width + gap), center_y - height / 2, bar_width, height)
            painter.drawRoundedRect(rect, bar_width / 2, bar_width / 2)


class MetricTile(CardWidget):
    """指标小卡片

    以「标题 + 数值」的形式展示一项指标。
    """

    def __init__(
        self,
        title: str,
        value: str = '--',
        color: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """初始化指标卡片

        Args:
            title: 指标名称
            value: 指标初始值
            color: 数值颜色，None 时使用默认文字颜色
            parent: 父组件
        """
        super().__init__(parent)
        self.setFixedHeight(88)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(2)

        self.value_label = TitleLabel(value, self)
        self.value_label.setFont(getFont(22, QFont.Weight.DemiBold))
        if color:
            self.value_label.setTextColor(QColor(color), QColor(color))

        layout.addWidget(CaptionLabel(title, self))
        layout.addWidget(self.value_label)

    def set_value(self, value: str, tooltip: str = '') -> None:
        """更新指标数值

        Args:
            value: 新数值
            tooltip: 鼠标悬停提示
        """
        self.value_label.setText(value)
        self.value_label.setToolTip(tooltip or value)

    def set_color(self, color: str) -> None:
        """更新数值颜色

        Args:
            color: 颜色（十六进制）
        """
        self.value_label.setTextColor(QColor(color), QColor(color))


class StepHeader(QWidget):
    """步骤标题

    圆形序号 + 标题 + 可选说明，用于克隆流程的步骤卡片。
    """

    def __init__(
        self,
        index: int,
        title: str,
        description: str = '',
        parent: QWidget | None = None,
    ) -> None:
        """初始化步骤标题

        Args:
            index: 步骤序号
            title: 步骤标题
            description: 步骤说明
            parent: 父组件
        """
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        number_label = QLabel(str(index), self)
        number_label.setFixedSize(26, 26)
        number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        number_label.setFont(getFont(12, QFont.Weight.DemiBold))
        number_label.setStyleSheet(f'color: white; background: {ACCENT}; border-radius: 13px;')
        layout.addWidget(number_label, 0, Qt.AlignmentFlag.AlignTop)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        title_label = BodyLabel(title, self)
        title_label.setFont(getFont(15, QFont.Weight.DemiBold))
        text_layout.addWidget(title_label)

        if description:
            desc_label = CaptionLabel(description, self)
            desc_label.setWordWrap(True)
            text_layout.addWidget(desc_label)

        layout.addLayout(text_layout, 1)
        layout.addStretch()
