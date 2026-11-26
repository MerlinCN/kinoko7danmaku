"""TTS 播报概览卡片"""

from PySide6.QtCore import Signal
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CaptionLabel, CardWidget, PushButton, SubtitleLabel

from core.const import SUPPORTED_SERVICES
from core.qconfig import cfg
from models.service import ServiceType


class _Metric(QWidget):
    """单个参数指标"""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        """初始化参数指标

        Args:
            title: 指标名称
            parent: 父组件
        """
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.value_label = BodyLabel('--', self)
        layout.addWidget(CaptionLabel(title, self))
        layout.addWidget(self.value_label)

    def set_value(self, value: str) -> None:
        """设置指标值

        Args:
            value: 指标值
        """
        self.value_label.setText(value)


class TtsSummaryCard(CardWidget):
    """TTS 播报概览卡片

    展示当前 TTS 服务、音色与常用参数，并提供跳转到设置的入口。
    """

    open_settings = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化 TTS 概览卡片

        Args:
            parent: 父组件
        """
        super().__init__(parent)
        self._init_ui()
        self._connect_signals()
        self.refresh()

    def _init_ui(self) -> None:
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()
        header_layout.addWidget(SubtitleLabel('TTS 播报', self))
        header_layout.addStretch()

        self.settings_btn = PushButton('去调整', self)
        self.settings_btn.clicked.connect(self._on_open_settings)
        header_layout.addWidget(self.settings_btn)
        layout.addLayout(header_layout)

        self.service_label = BodyLabel('--', self)
        self.voice_label = CaptionLabel('--', self)
        layout.addWidget(self.service_label)
        layout.addWidget(self.voice_label)

        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(16)
        self.speed_metric = _Metric('语速', self)
        self.volume_metric = _Metric('音量', self)
        self.pitch_metric = _Metric('音调', self)
        for metric in (self.speed_metric, self.volume_metric, self.pitch_metric):
            metrics_layout.addWidget(metric, 1)
        layout.addLayout(metrics_layout)

    def _connect_signals(self) -> None:
        """连接配置变化信号"""
        cfg.activeTTS.valueChanged.connect(self._on_config_changed)
        cfg.minimaxSpeed.valueChanged.connect(self._on_config_changed)
        cfg.minimaxVol.valueChanged.connect(self._on_config_changed)
        cfg.minimaxPitch.valueChanged.connect(self._on_config_changed)
        cfg.edgeRate.valueChanged.connect(self._on_config_changed)
        cfg.edgeVolume.valueChanged.connect(self._on_config_changed)
        cfg.edgePitch.valueChanged.connect(self._on_config_changed)

    def refresh(self) -> None:
        """刷新 TTS 概览"""
        service = ServiceType(cfg.activeTTS.value)
        detail = SUPPORTED_SERVICES[service]
        self.service_label.setText(detail.description)

        if service == ServiceType.MINIMAX:
            self.voice_label.setText(f'音色 · {cfg.minimaxVoiceId.value}')
            self._set_metrics(
                f'{cfg.minimaxSpeed.value:.1f}',
                f'{cfg.minimaxVol.value:.1f}',
                f'{cfg.minimaxPitch.value:.0f}',
            )
        elif service == ServiceType.EDGE:
            self.voice_label.setText(f'音色 · {cfg.edgeVoice.value}')
            self._set_metrics(
                f'{cfg.edgeRate.value:.1f}',
                f'{cfg.edgeVolume.value:.1f}',
                f'{cfg.edgePitch.value:.0f}',
            )
        else:
            self.voice_label.setText('参数请在设置中查看')
            self._set_metrics('--', '--', '--')

    def _set_metrics(self, speed: str, volume: str, pitch: str) -> None:
        """设置三个指标的值

        Args:
            speed: 语速
            volume: 音量
            pitch: 音调
        """
        self.speed_metric.set_value(speed)
        self.volume_metric.set_value(volume)
        self.pitch_metric.set_value(pitch)

    def _on_config_changed(self, _value: object) -> None:
        """配置变化时刷新"""
        self.refresh()

    def _on_open_settings(self, _checked: bool = False) -> None:
        """打开设置页"""
        self.open_settings.emit()

    def showEvent(self, event: QShowEvent) -> None:
        """页面显示时刷新"""
        super().showEvent(event)
        self.refresh()
