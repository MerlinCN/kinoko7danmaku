"""OmniVoice 本地服务界面"""

import time

from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QTimer, QUrl, Qt
from PySide6.QtGui import QShowEvent
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)
from loguru import logger
from qasync import asyncSlot
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    ComboBoxSettingCard,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    PushButton,
    ScrollArea,
    SettingCardGroup,
    Slider,
    StateToolTip,
    SubtitleLabel,
    TextEdit,
    ToolButton,
    qconfig,
)
from qfluentwidgets import (
    FluentIcon as FIF,
)
from qfluentwidgets.common.style_sheet import setCustomStyleSheet

from core.omnivoice_runtime import RuntimeProgress, RuntimeState, RuntimeStatus, omnivoice_runtime
from core.omnivoice_settings import load_settings, save_settings
from core.player import audio_player
from core.qconfig import cfg
from gui.components import HeroCard, IntSettingCard, MetricTile
from gui.components.minimax_kit import accent_button_qss, ghost_button_qss, hero_icon
from models.service import ServiceType
from tts_service.omnivoice import OmniVoiceService

ACCENT = '#4f6df5'


def _format_time(milliseconds: int) -> str:
    """把毫秒格式化为 分:秒:百分秒

    Args:
        milliseconds: 毫秒数

    Returns:
        形如 0:05:30 的文本（分:秒:百分秒）
    """
    seconds, hundredths = divmod(max(milliseconds, 0) // 10, 100)
    minutes, seconds = divmod(seconds, 60)
    return f'{minutes}:{seconds:02d}:{hundredths:02d}'


_STATUS_STYLE = {
    RuntimeStatus.NOT_INSTALLED: ('未安装', '#8a8a8a'),
    RuntimeStatus.INSTALLED: ('已安装', '#d99100'),
    RuntimeStatus.RUNNING: ('运行中', '#2fa84f'),
}


class OmniVoiceInterface(QWidget):
    """OmniVoice 本地服务界面

    先安装并启动本地服务，服务就绪后才展示合成参数与试听。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化界面

        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        self._busy = False
        self._state = RuntimeState()
        self._settings = load_settings()
        self._init_ui()
        self._init_audition()
        self._bind_config()
        self._bind_signals()

    def _init_ui(self) -> None:
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(20)

        self.hero = HeroCard(
            'OmniVoice',
            '本地运行',
            '小米AI 实验室新一代Kaldi 团队（k2-fsa）于2026 年4 月开源的零样本多语言语音克隆TTS 模型',
            self,
            accent=ACCENT,
        )
        self.install_button = PushButton('安装本地运行时', self.hero)
        self.install_button.setIcon(hero_icon(FIF.DOWNLOAD))
        setCustomStyleSheet(self.install_button, accent_button_qss(ACCENT), accent_button_qss(ACCENT))
        self.hero.add_action(self.install_button)

        self.start_button = PushButton('启动服务', self.hero)
        self.start_button.setIcon(hero_icon(FIF.PLAY))
        setCustomStyleSheet(self.start_button, accent_button_qss(ACCENT), accent_button_qss(ACCENT))
        self.hero.add_action(self.start_button)

        self.stop_button = PushButton('停止服务', self.hero)
        self.stop_button.setIcon(hero_icon(FIF.PAUSE))
        setCustomStyleSheet(self.stop_button, ghost_button_qss(), ghost_button_qss())
        self.hero.add_action(self.stop_button)

        self.use_button = PushButton('设为当前 TTS', self.hero)
        self.use_button.setIcon(hero_icon(FIF.ACCEPT))
        setCustomStyleSheet(self.use_button, accent_button_qss(ACCENT), accent_button_qss(ACCENT))
        self.hero.add_action(self.use_button)

        self.hero.setFixedHeight(178)
        layout.addWidget(self.hero)
        scroll_area = ScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet('QScrollArea { border: none; background: transparent; }')

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(20)

        metric_layout = QHBoxLayout()
        metric_layout.setSpacing(12)
        self.status_metric = MetricTile('运行状态', '--', ACCENT, self)
        self.device_metric = MetricTile('推理设备', '--', parent=self)
        self.size_metric = MetricTile('模型体积', '--', parent=self)
        self.active_metric = MetricTile('当前 TTS', '--', parent=self)
        for tile in (self.status_metric, self.device_metric, self.size_metric, self.active_metric):
            metric_layout.addWidget(tile, 1)
        scroll_layout.addLayout(metric_layout)

        self.runtime_group = SettingCardGroup('启动参数', scroll_widget)
        self.port_card = IntSettingCard(
            cfg.omnivoicePort,
            FIF.CONNECT,
            '服务端口',
            '本地合成服务监听的端口',
            self.runtime_group,
            placeholder='8017',
        )
        self.source_card = ComboBoxSettingCard(
            cfg.omnivoiceHfEndpoint,
            FIF.DOWNLOAD,
            '模型下载源',
            '首次启动时从这个站点下载模型',
            texts=['https://hf-mirror.com', 'https://huggingface.co'],
            parent=self.runtime_group,
        )
        self.runtime_group.addSettingCard(self.port_card)
        self.runtime_group.addSettingCard(self.source_card)
        scroll_layout.addWidget(self.runtime_group)

        self.param_card = self._build_param_card()
        scroll_layout.addWidget(self.param_card)

        self.preview_card = self._build_preview_card()
        scroll_layout.addWidget(self.preview_card)

        scroll_layout.addStretch(1)

        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)

    def _build_param_card(self) -> CardWidget:
        """构建合成参数卡片

        Returns:
            卡片组件
        """
        card = CardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(12)

        card_layout.addWidget(SubtitleLabel('合成参数', card))

        card_layout.addWidget(BodyLabel('参考音频', card))
        audio_layout = QHBoxLayout()
        audio_layout.setSpacing(8)
        self.audio_button = PushButton('选择音频文件', card)
        self.audio_button.setIcon(FIF.FOLDER)
        self.audio_label = CaptionLabel('未选择参考音频，将使用模型自动音色', card)
        self.audio_play_button = ToolButton(FIF.PLAY, card)
        self.audio_play_button.setToolTip('试听参考音频')
        self.clear_audio_button = ToolButton(FIF.DELETE, card)
        self.clear_audio_button.setToolTip('清除参考音频')
        audio_layout.addWidget(self.audio_button)
        audio_layout.addWidget(self.audio_label, 1)
        audio_layout.addWidget(self.audio_play_button)
        audio_layout.addWidget(self.clear_audio_button)
        card_layout.addLayout(audio_layout)

        self.audition_row = QWidget(card)
        audition_layout = QHBoxLayout(self.audition_row)
        audition_layout.setContentsMargins(0, 0, 0, 0)
        audition_layout.setSpacing(10)
        self.audition_slider = Slider(Qt.Orientation.Horizontal, self.audition_row)
        # 手柄是独立子控件会吃掉鼠标事件，点在手柄上就拖不动，这里让事件落到进度条本身
        self.audition_slider.handle.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.audition_slider.installEventFilter(self)
        self.audition_time = CaptionLabel('0:00:00 / 0:00:00', self.audition_row)
        audition_layout.addWidget(self.audition_slider, 1)
        audition_layout.addWidget(self.audition_time)
        card_layout.addWidget(self.audition_row)
        self.audition_row.hide()

        card_layout.addWidget(BodyLabel('参考音频文本', card))
        self.ref_text_edit = LineEdit(card)
        self.ref_text_edit.setPlaceholderText('参考音频里说了什么，留空则由模型自动识别，填了可以增强模型能力')
        card_layout.addWidget(self.ref_text_edit)

        speed_header = QHBoxLayout()
        speed_header.addWidget(BodyLabel('语速', card))
        self.speed_label = CaptionLabel('1.0', card)
        speed_header.addStretch(1)
        speed_header.addWidget(self.speed_label)
        card_layout.addLayout(speed_header)

        self.speed_slider = Slider(Qt.Orientation.Horizontal, card)
        self.speed_slider.setRange(5, 20)
        card_layout.addWidget(self.speed_slider)
        return card

    def _build_preview_card(self) -> CardWidget:
        """构建试听卡片

        Returns:
            卡片组件
        """
        card = CardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(12)

        card_layout.addWidget(SubtitleLabel('试听', card))

        self.preview_edit = TextEdit(card)
        self.preview_edit.setPlaceholderText('输入要合成的文本，例如：欢迎来到直播间')
        self.preview_edit.setFixedHeight(100)
        card_layout.addWidget(self.preview_edit)

        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)
        self.play_button = PushButton('合成并播放', card)
        self.play_button.setIcon(FIF.SPEAKERS)
        setCustomStyleSheet(self.play_button, accent_button_qss(ACCENT), accent_button_qss(ACCENT))
        action_layout.addWidget(self.play_button)
        action_layout.addStretch(1)
        card_layout.addLayout(action_layout)
        return card

    def _bind_config(self) -> None:
        """把配置值回填到控件"""
        self.ref_text_edit.setText(self._settings.ref_text)

        speed = round(self._settings.speed, 1)
        self.speed_slider.setValue(round(speed * 10))
        self.speed_label.setText(f'{speed:.1f}')

        path = self._settings.ref_audio
        if path and Path(path).exists():
            self.audio_label.setText(Path(path).name)
            self._load_audition(path)
        elif path:
            self.audio_label.setText(f'文件不存在: {path}')

    def _bind_signals(self) -> None:
        """连接控件信号，绑定配置之后调用，避免初始化时写配置"""
        self.install_button.clicked.connect(self._install)
        self.start_button.clicked.connect(self._start_service)
        self.stop_button.clicked.connect(self._on_stop)
        self.use_button.clicked.connect(self._on_use_as_active)
        self.play_button.clicked.connect(self._on_preview_play)
        self.audio_button.clicked.connect(self._on_pick_audio)
        self.audio_play_button.clicked.connect(self._on_toggle_audition)
        self.clear_audio_button.clicked.connect(self._on_clear_audio)
        self.audition_slider.sliderMoved.connect(self._on_audition_seek)
        self.audition_slider.clicked.connect(self._on_audition_seek)
        self.media_player.positionChanged.connect(self._on_audition_position)
        self.media_player.durationChanged.connect(self._on_audition_duration)
        self.media_player.playbackStateChanged.connect(self._on_audition_state)
        self.media_player.errorOccurred.connect(self._on_audition_error)
        self.ref_text_edit.editingFinished.connect(self._on_ref_text_changed)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)

    def showEvent(self, event: QShowEvent) -> None:
        """显示页面时刷新运行时状态

        Args:
            event: 显示事件
        """
        super().showEvent(event)
        self._refresh_state()

    def _on_speed_changed(self, value: int) -> None:
        """语速滑块变化

        Args:
            value: 滑块刻度（1 刻 = 0.1）
        """
        speed = round(value / 10, 1)
        self.speed_label.setText(f'{speed:.1f}')
        self._settings.speed = speed
        save_settings(self._settings)

    def _on_ref_text_changed(self) -> None:
        """参考音频文本输入完成"""
        self._settings.ref_text = self.ref_text_edit.text()
        save_settings(self._settings)

    def _on_pick_audio(self) -> None:
        """选择参考音频"""
        path, _filter = QFileDialog.getOpenFileName(
            self,
            '选择参考音频',
            '',
            '音频文件 (*.wav *.mp3 *.flac *.m4a)',
        )
        if not path:
            return
        self._settings.ref_audio = path
        save_settings(self._settings)
        self.audio_label.setText(Path(path).name)
        self.audio_label.setToolTip(path)
        self._load_audition(path)

    def _on_clear_audio(self) -> None:
        """清除参考音频"""
        self._settings.ref_audio = ''
        save_settings(self._settings)
        self.audio_label.setText('未选择参考音频，将使用模型自动音色')
        self.audio_label.setToolTip('')
        self.media_player.stop()
        self.media_player.setSource(QUrl())
        self._audition_anchor = 0
        self._audition_anchor_time = 0.0
        self.audition_row.hide()

    def _init_audition(self) -> None:
        """初始化参考音频试听播放器"""
        self.media_output = QAudioOutput(self)
        self.media_player = QMediaPlayer(self)
        self.media_player.setAudioOutput(self.media_output)
        self.media_output.setVolume(1.0)

        self._audition_anchor = 0
        self._audition_anchor_time = 0.0
        self._audition_dragging = False
        self._audition_timer = QTimer(self)
        self._audition_timer.setInterval(33)
        self._audition_timer.timeout.connect(self._sync_audition_value)

    def _load_audition(self, path: str) -> None:
        """载入参考音频用于试听

        Args:
            path: 音频文件路径
        """
        self.media_player.stop()
        self.media_player.setSource(QUrl.fromLocalFile(path))
        self.audio_play_button.setIcon(FIF.PLAY)
        self._audition_anchor = 0
        self._audition_anchor_time = 0.0
        self.audition_slider.setValue(0)
        self.audition_time.setText('0:00 / 0:00')
        self.audition_row.show()

    def _on_toggle_audition(self) -> None:
        """播放或暂停参考音频"""
        if self.media_player.source().isEmpty():
            return
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            return
        self.media_player.play()

    def _sync_audition_value(self) -> None:
        """按播放位置刷新进度条与时间文本

        `positionChanged` 只有约 85ms 的精度（受音频缓冲影响），直接用手柄跟着它
        会一步跳十几个像素。这里在最近一次播放位置的基础上按时钟插值，让手柄连续移动。
        """
        if self._audition_dragging:
            return

        duration = max(self.media_player.duration(), 0)
        position = self._display_position()
        self.audition_slider.setValue(position)
        self.audition_time.setText(f'{_format_time(position)} / {_format_time(duration)}')

    def _display_position(self) -> int:
        """按播放状态推算当前应显示的播放位置

        Returns:
            毫秒位置：播放中按最近一次位置加经过时间插值，其余情况直接用播放器位置
        """
        position = self.media_player.position()
        if self.media_player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
            return position
        if not self._audition_anchor_time:
            return position

        elapsed = int((time.monotonic() - self._audition_anchor_time) * 1000)
        position = self._audition_anchor + elapsed
        duration = self.media_player.duration()
        return min(position, duration) if duration > 0 else position

    def _on_audition_position(self, position: int) -> None:
        """记录播放位置并刷新进度

        Args:
            position: 当前位置（毫秒）
        """
        self._audition_anchor = position
        self._audition_anchor_time = time.monotonic()
        self._sync_audition_value()

    def _on_audition_duration(self, duration: int) -> None:
        """音频时长变化时重置进度条

        Args:
            duration: 时长（毫秒）
        """
        self.audition_slider.setRange(0, max(duration, 0))
        self._sync_audition_value()

    def _on_audition_state(self, state: QMediaPlayer.PlaybackState) -> None:
        """切换播放/暂停图标与插值定时器

        Args:
            state: 播放状态
        """
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.audio_play_button.setIcon(FIF.PAUSE if playing else FIF.PLAY)
        self._audition_anchor = self.media_player.position()
        self._audition_anchor_time = 0.0
        if playing:
            self._audition_timer.start()
        else:
            self._audition_timer.stop()
        self._sync_audition_value()

    def _on_audition_error(self, error: QMediaPlayer.Error, message: str) -> None:
        """记录试听失败原因

        Args:
            error: 错误类型
            message: 错误描述
        """
        if error != QMediaPlayer.Error.NoError:
            logger.warning(f'试听参考音频失败: {message}')

    def _on_audition_seek(self, position: int) -> None:
        """点击或拖动进度条跳转

        Args:
            position: 目标位置（毫秒）
        """
        self._audition_anchor = position
        self._audition_anchor_time = time.monotonic()
        self.media_player.setPosition(position)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """跟踪进度条上的鼠标按下状态

        qfluentwidgets 的 `Slider` 点击/拖动都不走 `QSlider` 的按下流程，
        `isSliderDown()` 永远是 False，这里补一个标记，拖动期间暂停进度刷新。

        Args:
            watched: 事件来源
            event: 事件对象

        Returns:
            是否拦截事件，这里始终交回原控件处理
        """
        if watched is self.audition_slider:
            if event.type() == QEvent.Type.MouseButtonPress:
                self._audition_dragging = True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                self._audition_dragging = False
        return super().eventFilter(watched, event)

    def _on_use_as_active(self) -> None:
        """把当前 TTS 切换为 OmniVoice"""
        qconfig.set(cfg.activeTTS, ServiceType.OMNIVOICE)
        self._refresh_state()
        InfoBar.success(
            title='已切换',
            content='当前 TTS 服务已切换为 OmniVoice 本地',
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self,
        )

    def _show_toast(self, title: str, content: str) -> StateToolTip:
        """显示状态提示

        Args:
            title: 标题
            content: 内容

        Returns:
            提示组件
        """
        tooltip = StateToolTip(title, content, self.window())
        tooltip.move(tooltip.getSuitablePos())
        tooltip.show()
        return tooltip

    @staticmethod
    def _toast_progress(tooltip: StateToolTip, progress: RuntimeProgress) -> None:
        """把进度写进提示

        Args:
            tooltip: 提示组件
            progress: 进度对象
        """
        if progress.percent is None:
            tooltip.setContent(progress.message)
        else:
            tooltip.setContent(f'{progress.message}（{progress.percent}%）')

    def _set_busy(self, *, busy: bool) -> None:
        """切换忙碌状态

        Args:
            busy: 是否忙碌
        """
        self._busy = busy
        for button in (self.install_button, self.start_button, self.stop_button, self.use_button):
            button.setEnabled(not busy)
        self.play_button.setEnabled(not busy)

    @asyncSlot()
    async def _install(self) -> None:
        """安装本地运行时"""
        self._set_busy(busy=True)
        toast = self._show_toast('正在安装本地运行时', '正在准备…')
        try:
            await omnivoice_runtime.install(
                cfg.omnivoiceHfEndpoint.value,
                lambda progress: self._toast_progress(toast, progress),
            )
        except Exception as e:
            logger.warning(f'安装 OmniVoice 运行时失败: {e!r}')
            toast.setState(False)
            toast.setTitle('安装失败')
            toast.setContent(str(e))
            self._set_busy(busy=False)
            return
        toast.setState(True)
        toast.setTitle('安装完成')
        toast.setContent('可以启动本地服务了')
        self._set_busy(busy=False)
        await self._refresh_state()

    @asyncSlot()
    async def _start_service(self) -> bool:
        """启动本地服务

        Returns:
            服务启动成功时返回 True
        """
        self._set_busy(busy=True)
        toast = self._show_toast('正在启动本地服务', '正在准备…')
        try:
            await omnivoice_runtime.start(
                cfg.omnivoicePort.value,
                cfg.omnivoiceHfEndpoint.value,
                lambda progress: self._toast_progress(toast, progress),
            )
        except Exception as e:
            logger.warning(f'启动 OmniVoice 服务失败: {e!r}')
            toast.setState(False)
            toast.setTitle('启动失败')
            toast.setContent(str(e))
            self._set_busy(busy=False)
            return False
        toast.setState(True)
        toast.setTitle('服务已就绪')
        toast.setContent(f'127.0.0.1:{cfg.omnivoicePort.value}')
        self._set_busy(busy=False)
        await self._refresh_state()
        return True

    async def _service_ready(self) -> bool:
        """确保本地服务在运行

        Returns:
            服务可用时返回 True
        """
        state = await omnivoice_runtime.state(cfg.omnivoicePort.value)
        if state.status == RuntimeStatus.RUNNING:
            return True
        return await self._start_service()

    @asyncSlot()
    async def _on_stop(self) -> None:
        """停止本地服务"""
        await omnivoice_runtime.stop(cfg.omnivoicePort.value)
        await self._refresh_state()

    @asyncSlot()
    async def _on_preview_play(self) -> None:
        """合成并播放试听文本"""
        text = self.preview_edit.toPlainText().strip()
        if not text:
            InfoBar.warning(
                title='没有可合成的文本',
                content='请先在试听框里输入内容',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
            return

        if not await self._service_ready():
            return

        self.media_player.pause()
        self.play_button.setEnabled(False)
        toast = self._show_toast('正在合成', '本地 OmniVoice 正在生成语音…')
        started = time.monotonic()
        try:
            audio = await OmniVoiceService().text_to_speech(text)
            await audio_player.play_bytes_async(audio)
        except Exception as e:
            logger.warning(f'OmniVoice 试听失败: {e!r}')
            toast.setState(False)
            toast.setTitle('合成失败')
            toast.setContent(str(e))
            return
        finally:
            self.play_button.setEnabled(True)

        elapsed = time.monotonic() - started
        toast.setState(True)
        toast.setTitle('合成完成')
        toast.setContent(f'{len(audio) / 1024:.0f} KB · 耗时 {elapsed:.1f}s，已送入播放队列')

    @asyncSlot()
    async def _refresh_state(self) -> None:
        """刷新运行时状态、指标与可见区域"""
        state = await omnivoice_runtime.state(cfg.omnivoicePort.value)
        self._state = state
        text, color = _STATUS_STYLE[state.status]
        running = state.status == RuntimeStatus.RUNNING
        installed = state.status != RuntimeStatus.NOT_INSTALLED
        active = cfg.activeTTS.value == ServiceType.OMNIVOICE

        self.status_metric.set_value(text, state.detail)
        self.status_metric.set_color(color)

        self.param_card.setVisible(running)
        self.preview_card.setVisible(running)
        self.runtime_group.setVisible(not running)

        self.install_button.setVisible(not installed)
        self.install_button.setEnabled(not self._busy)
        self.start_button.setVisible(installed and not running)
        self.start_button.setEnabled(not self._busy)
        self.stop_button.setVisible(running)
        self.stop_button.setEnabled(not self._busy)
        self.use_button.setVisible(running)
        self.use_button.setText('当前 TTS' if active else '设为当前 TTS')
        self.use_button.setEnabled(not active and not self._busy)

        self.active_metric.set_value('是' if active else '否')
        self.active_metric.set_color('#2fa84f' if active else '#8a8a8a')
        self._refresh_detail_metrics()

    def _refresh_detail_metrics(self) -> None:
        """刷新设备与模型体积指标"""
        try:
            backend = omnivoice_runtime.backend()
        except RuntimeError as e:
            self.device_metric.set_value('不支持', str(e))
        else:
            self.device_metric.set_value(backend.device_map.upper(), backend.description)

        size = omnivoice_runtime.cached_model_bytes()
        if size > 0:
            self.size_metric.set_value(f'{size / 1024**3:.1f} GB')
        else:
            self.size_metric.set_value('--', '启动服务时会自动下载模型')
