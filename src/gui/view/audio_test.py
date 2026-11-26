"""音频测试界面"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from loguru import logger
from qasync import asyncSlot
from qfluentwidgets import (
    CaptionLabel,
    CardWidget,
    ExpandLayout,
    IconWidget,
    InfoBar,
    InfoBarPosition,
    PrimaryPushButton,
    PushButton,
    ScrollArea,
    SettingCardGroup,
    SubtitleLabel,
    TextEdit,
    TitleLabel,
)
from qfluentwidgets import (
    FluentIcon as FIF,
)

from core.const import SUPPORTED_SERVICES
from core.player import audio_player
from core.qconfig import cfg
from gui.components import ReadOnlyInfoCard
from models.service import ServiceType
from tts_service import get_tts_service


def _format_voice(voice_id: str) -> str:
    """将音色 ID 格式化为「显示名（ID）」

    Args:
        voice_id: 音色 ID

    Returns:
        str: 用于展示的文本
    """
    if not voice_id:
        return '（未设置）'
    voice_dict = cfg.voiceDict.value
    name = voice_dict.get(voice_id)
    if name and name != voice_id:
        return f'{name}（{voice_id}）'
    return voice_id


class AudioDeviceCard(CardWidget):
    """当前输出设备卡片

    展示音频实际播放到的设备，并提供跳转到设置更换设备的入口。
    """

    open_settings = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化输出设备卡片

        Args:
            parent: 父组件
        """
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        icon_widget = IconWidget(FIF.SPEAKERS, self)
        icon_widget.setFixedSize(32, 32)
        layout.addWidget(icon_widget, 0, Qt.AlignmentFlag.AlignVCenter)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        self.device_label = SubtitleLabel('--', self)
        self.detail_label = CaptionLabel('设备索引 --', self)
        info_layout.addWidget(self.device_label)
        info_layout.addWidget(self.detail_label)
        layout.addLayout(info_layout, 1)

        self.switch_btn = PushButton('更换设备', self)
        self.switch_btn.setIcon(FIF.SETTING)
        self.switch_btn.clicked.connect(self.open_settings.emit)
        layout.addWidget(self.switch_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        self.setFixedHeight(76)
        self.refresh()

    def refresh(self) -> None:
        """刷新当前输出设备"""
        device = audio_player.get_current_output_device()
        if device is None:
            self.device_label.setText('未检测到输出设备')
            self.detail_label.setText('请检查系统音频设备')
            return

        self.device_label.setText(device.name)
        details = [f'设备索引 {device.index}']
        if device.sample_rate:
            details.append(f'{device.sample_rate} Hz')
        if device.channels:
            details.append(f'{device.channels} 声道')
        self.detail_label.setText(' · '.join(details))


class TtsTestCard(CardWidget):
    """语音合成测试卡片

    输入文本后使用当前 TTS 服务合成并播放。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化语音合成测试卡片

        Args:
            parent: 父组件
        """
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        header_layout.addWidget(SubtitleLabel('语音合成测试', self))
        header_layout.addStretch()
        self.service_label = CaptionLabel('', self)
        header_layout.addWidget(self.service_label, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(header_layout)

        self.text_edit = TextEdit(self)
        self.text_edit.setPlaceholderText('输入要合成的文本…')
        self.text_edit.setFixedHeight(140)
        layout.addWidget(self.text_edit)

        footer_layout = QHBoxLayout()
        footer_layout.addWidget(CaptionLabel('使用当前服务与参数合成，并播放到上方输出设备', self))
        footer_layout.addStretch()

        self.test_btn = PrimaryPushButton('合成并播放', self)
        self.test_btn.setIcon(FIF.PLAY)
        footer_layout.addWidget(self.test_btn)
        layout.addLayout(footer_layout)

        # ExpandLayout 按 widget.height() 摆放，不会读 sizeHint
        self.setFixedHeight(layout.sizeHint().height())


class AudioTestInterface(ScrollArea):
    """音频测试界面

    展示当前输出设备与 TTS 参数，并提供合成播放测试。
    """

    open_settings = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化音频测试界面

        Args:
            parent: 父组件
        """
        super().__init__(parent=parent)
        self.scrollWidget = QWidget()
        self.expandLayout = ExpandLayout(self.scrollWidget)

        self._init_ui()
        self._init_layout()
        self._connect_signals()
        self._on_active_tts_changed()

    def _init_ui(self) -> None:
        """初始化 UI 组件"""
        # 标题
        self.title_label = TitleLabel('音频测试', self)

        # 输出设备
        self.device_card = AudioDeviceCard(self.scrollWidget)
        self.device_card.open_settings.connect(self.open_settings.emit)

        # 语音合成测试
        self.test_card = TtsTestCard(self.scrollWidget)

        # 参数展示分组
        self.minimaxGroup = self._build_minimax_group()

    def _build_minimax_group(self) -> SettingCardGroup:
        """构建 Minimax 当前参数分组"""
        group = SettingCardGroup('Minimax 当前参数', self.scrollWidget)
        group.addSettingCard(
            ReadOnlyInfoCard(
                configItem=cfg.minimaxApiKey,
                icon=FIF.EDIT,
                title='API Key',
                content='调用 Minimax TTS 时使用的 API 密钥',
                mask=True,
                parent=group,
            )
        )
        self.minimaxVoiceCard = ReadOnlyInfoCard(
            configItem=cfg.minimaxVoiceId,
            icon=FIF.MICROPHONE,
            title='音色',
            content='当前使用的 Minimax 音色',
            formatter=_format_voice,
            parent=group,
        )
        group.addSettingCard(self.minimaxVoiceCard)
        group.addSettingCard(
            ReadOnlyInfoCard(
                configItem=cfg.minimaxModel,
                icon=FIF.ROBOT,
                title='模型',
                content='当前使用的 Minimax 模型',
                parent=group,
            )
        )
        group.addSettingCard(
            ReadOnlyInfoCard(
                configItem=cfg.minimaxSpeed,
                icon=FIF.SPEED_OFF,
                title='语速',
                content='当前的语音播放速度',
                parent=group,
            )
        )
        group.addSettingCard(
            ReadOnlyInfoCard(
                configItem=cfg.minimaxVol,
                icon=FIF.VOLUME,
                title='音量',
                content='当前的语音音量',
                parent=group,
            )
        )
        group.addSettingCard(
            ReadOnlyInfoCard(
                configItem=cfg.minimaxPitch,
                icon=FIF.MUSIC,
                title='音调',
                content='当前的语音音调',
                parent=group,
            )
        )
        return group

    def _init_layout(self) -> None:
        """初始化布局"""
        self.title_label.move(36, 30)

        self.expandLayout.setSpacing(24)
        self.expandLayout.setContentsMargins(36, 10, 36, 10)
        self.expandLayout.addWidget(self.device_card)
        self.expandLayout.addWidget(self.test_card)
        self.expandLayout.addWidget(self.minimaxGroup)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 80, 0, 20)
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)

        self.scrollWidget.setObjectName('scrollWidget')
        self.title_label.setObjectName('titleLabel')

    def _connect_signals(self) -> None:
        """连接信号"""
        self.test_card.test_btn.clicked.connect(self._on_test_button_clicked)
        cfg.activeTTS.valueChanged.connect(self._on_active_tts_changed)
        cfg.voiceDict.valueChanged.connect(self._refresh_voice_display)
        cfg.playerDevice.valueChanged.connect(self.device_card.refresh)

    def _on_active_tts_changed(self, *_: object) -> None:
        """根据当前激活的 TTS 服务切换参数分组的可见性"""
        active = cfg.activeTTS.value
        self.minimaxGroup.setVisible(active == ServiceType.MINIMAX)

        service = ServiceType(active)
        self.test_card.service_label.setText(f'当前服务 · {SUPPORTED_SERVICES[service].description}')

    def _refresh_voice_display(self, *_: object) -> None:
        """voiceDict 变更时，重新格式化音色显示文本

        音色 ID 没变所以 valueChanged 不会触发，需要手动重算一次。
        """
        self.minimaxVoiceCard.refresh()

    @asyncSlot()
    async def _on_test_button_clicked(self) -> None:
        """测试按钮点击事件"""
        text = self.test_card.text_edit.toPlainText().strip()
        if not text:
            InfoBar.warning(
                title='请输入文本',
                content='需要输入要合成的文本后才能测试',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
            return

        try:
            tts_service = get_tts_service()
            audio = await tts_service.text_to_speech(text)
            await audio_player.play_bytes_async(audio)
        except Exception as e:
            logger.exception(f'音频测试失败: {e}')
            InfoBar.error(
                title='测试失败',
                content=str(e),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )

    def showEvent(self, event: QShowEvent) -> None:
        """页面显示时刷新输出设备"""
        super().showEvent(event)
        self.device_card.refresh()
