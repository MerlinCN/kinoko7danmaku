"""MiniMax 主页"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QMouseEvent, QShowEvent
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from loguru import logger
from qasync import asyncSlot
from qfluentwidgets import BodyLabel, CardWidget, IconWidget, PushButton, SubtitleLabel
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets.common.icon import FluentIconBase
from qfluentwidgets.common.style_sheet import setCustomStyleSheet

from core.qconfig import cfg
from gui.components.minimax_kit import ACCENT, HeroCard, MetricTile, accent_button_qss, ghost_button_qss
from tts_service.minimax import MinimaxService

_OK_COLOR = '#2fa84f'
_WARN_COLOR = '#d99145'


def _format_voice(voice_id: str) -> str:
    """将音色 ID 格式化为可读名称

    Args:
        voice_id: 音色 ID

    Returns:
        str: 展示文本
    """
    if not voice_id:
        return '未设置'
    name = cfg.voiceDict.value.get(voice_id)
    return name if name and name != voice_id else voice_id


class EntryCard(CardWidget):
    """功能入口卡片"""

    clicked = Signal()

    def __init__(
        self,
        icon: str | QIcon | FluentIconBase,
        title: str,
        description: str,
        parent: QWidget | None = None,
    ) -> None:
        """初始化功能入口卡片

        Args:
            icon: 图标
            title: 标题
            description: 描述
            parent: 父组件
        """
        super().__init__(parent)
        self.setFixedHeight(118)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 16, 16)
        layout.setSpacing(16)

        icon_widget = IconWidget(icon, self)
        icon_widget.setFixedSize(28, 28)
        layout.addWidget(icon_widget, 0, Qt.AlignmentFlag.AlignVCenter)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        text_layout.addWidget(SubtitleLabel(title, self))
        desc_label = BodyLabel(description, self)
        desc_label.setWordWrap(True)
        text_layout.addWidget(desc_label)
        layout.addLayout(text_layout, 1)

        arrow = IconWidget(FIF.CHEVRON_RIGHT, self)
        arrow.setFixedSize(16, 16)
        layout.addWidget(arrow, 0, Qt.AlignmentFlag.AlignVCenter)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """点击卡片时发出信号

        Args:
            event: 鼠标事件
        """
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


class MinimaxHomeInterface(QWidget):
    """MiniMax 主页

    展示服务概况、当前配置与音色相关入口。
    """

    open_voice_list = Signal()
    open_voice_clone = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化 MiniMax 主页

        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        self._tts_service = MinimaxService()
        self._voice_count_loaded = False

        self._init_ui()
        self._connect_signals()
        self._refresh_config_metrics()

    def _init_ui(self) -> None:
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(20)

        self.hero = HeroCard(
            'MiniMax Speech',
            '让弹幕拥有自己的声音',
            '挑选系统音色或克隆属于你的声音，把直播间里的每一句话念出来。',
            self,
        )
        browse_btn = PushButton('浏览音色', self.hero)
        browse_btn.setIcon(FIF.MUSIC_FOLDER)
        setCustomStyleSheet(browse_btn, accent_button_qss(), accent_button_qss())
        browse_btn.clicked.connect(self.open_voice_list.emit)
        self.hero.add_action(browse_btn)

        clone_btn = PushButton('克隆音色', self.hero)
        clone_btn.setIcon(FIF.MICROPHONE)
        setCustomStyleSheet(clone_btn, ghost_button_qss(), ghost_button_qss())
        clone_btn.clicked.connect(self.open_voice_clone.emit)
        self.hero.add_action(clone_btn)
        layout.addWidget(self.hero)

        metric_layout = QHBoxLayout()
        metric_layout.setSpacing(12)
        self.voice_metric = MetricTile('音色数量', '--', ACCENT, self)
        self.current_voice_metric = MetricTile('当前音色', '--', parent=self)
        self.model_metric = MetricTile('当前模型', '--', parent=self)
        self.api_metric = MetricTile('API Key', '--', parent=self)
        for tile in (self.voice_metric, self.current_voice_metric, self.model_metric, self.api_metric):
            metric_layout.addWidget(tile, 1)
        layout.addLayout(metric_layout)

        entry_layout = QHBoxLayout()
        entry_layout.setSpacing(12)

        self.voice_list_card = EntryCard(
            FIF.LIBRARY,
            '音色列表',
            '浏览可用音色，逐一试听后再决定使用哪一个',
            self,
        )
        self.voice_list_card.clicked.connect(self.open_voice_list.emit)
        entry_layout.addWidget(self.voice_list_card, 1)

        self.voice_clone_card = EntryCard(
            FIF.SAVE,
            '音色克隆',
            '上传一段人声，生成只属于你的音色',
            self,
        )
        self.voice_clone_card.clicked.connect(self.open_voice_clone.emit)
        entry_layout.addWidget(self.voice_clone_card, 1)

        layout.addLayout(entry_layout)
        layout.addStretch(1)

    def _connect_signals(self) -> None:
        """连接配置变化信号"""
        cfg.minimaxVoiceId.valueChanged.connect(self._refresh_config_metrics)
        cfg.voiceDict.valueChanged.connect(self._refresh_config_metrics)
        cfg.minimaxModel.valueChanged.connect(self._refresh_config_metrics)
        cfg.minimaxApiKey.valueChanged.connect(self._refresh_config_metrics)

    def refresh(self) -> None:
        """刷新指标数据"""
        self._refresh_config_metrics()
        self._load_voice_count()

    def _refresh_config_metrics(self, *_: object) -> None:
        """刷新当前配置相关指标"""
        self.current_voice_metric.set_value(_format_voice(cfg.minimaxVoiceId.value))
        self.model_metric.set_value(cfg.minimaxModel.value)

        if cfg.minimaxApiKey.value:
            self.api_metric.set_value('已配置')
            self.api_metric.set_color(_OK_COLOR)
        else:
            self.api_metric.set_value('未配置')
            self.api_metric.set_color(_WARN_COLOR)

    @asyncSlot()
    async def _load_voice_count(self) -> None:
        """加载可用音色数量"""
        if not cfg.minimaxApiKey.value:
            self.voice_metric.set_value('--', '请先配置 MiniMax API Key')
            return

        if self._voice_count_loaded:
            return

        try:
            response = await self._tts_service.get_voice_list()
        except Exception as e:
            logger.warning(f'获取音色数量失败: {e!r}')
            self.voice_metric.set_value('--', '获取失败，可进入音色列表重试')
            return

        self._voice_count_loaded = True
        self.voice_metric.set_value(str(len(response.voice_cloning)))

    def showEvent(self, event: QShowEvent) -> None:
        """页面显示时刷新数据"""
        super().showEvent(event)
        self.refresh()
