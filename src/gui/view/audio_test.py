"""音频测试界面"""

from loguru import logger
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qasync import asyncSlot
from qfluentwidgets import (
    CardWidget,
    ExpandLayout,
    InfoBar,
    InfoBarPosition,
    ScrollArea,
    SettingCardGroup,
    TextEdit,
    TitleLabel,
    ToolButton,
)
from qfluentwidgets import (
    FluentIcon as FIF,
)

from core.player import audio_player
from core.qconfig import cfg
from models.service import ServiceType
from tts_service import get_tts_service

from ..components import ReadOnlyInfoCard


def _format_voice(voice_id: str) -> str:
    """将音色 ID 格式化为「显示名（ID）」

    Args:
        voice_id: 音色 ID

    Returns:
        str: 用于展示的文本
    """
    if not voice_id:
        return "（未设置）"
    voice_dict = cfg.voiceDict.value
    name = voice_dict.get(voice_id)
    if name and name != voice_id:
        return f"{name}（{voice_id}）"
    return voice_id


class AudioTestInterface(ScrollArea):
    """音频测试界面

    用于测试 TTS 语音合成功能，并展示当前 TTS 服务使用的参数。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
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
        self.title_label = TitleLabel("音频测试", self)

        # 测试卡片
        self.test_card = CardWidget(self.scrollWidget)
        card_layout = QVBoxLayout(self.test_card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)

        self.text_edit = TextEdit()
        self.text_edit.setPlaceholderText("请输入要测试的文本...")
        self.text_edit.setMinimumHeight(200)
        card_layout.addWidget(self.text_edit)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.test_button = ToolButton(FIF.PLAY)
        button_layout.addWidget(self.test_button)
        card_layout.addLayout(button_layout)

        # ExpandLayout 按 widget.height() 摆放，不会读 sizeHint，
        # 必须主动把测试卡撑到内容需要的高度。
        self.test_card.setFixedHeight(card_layout.sizeHint().height())

        # 参数展示分组
        self.minimaxGroup = self._build_minimax_group()
        self.fishSpeechGroup = self._build_fish_speech_group()
        self.gptSovitsGroup = self._build_gpt_sovits_group()

    def _build_minimax_group(self) -> SettingCardGroup:
        """构建 Minimax 当前参数分组"""
        group = SettingCardGroup("Minimax 当前参数", self.scrollWidget)
        group.addSettingCard(
            ReadOnlyInfoCard(
                configItem=cfg.minimaxApiKey,
                icon=FIF.EDIT,
                title="API Key",
                content="调用 Minimax TTS 时使用的 API 密钥",
                mask=True,
                parent=group,
            )
        )
        self.minimaxVoiceCard = ReadOnlyInfoCard(
            configItem=cfg.minimaxVoiceId,
            icon=FIF.MICROPHONE,
            title="音色",
            content="当前使用的 Minimax 音色",
            formatter=_format_voice,
            parent=group,
        )
        group.addSettingCard(self.minimaxVoiceCard)
        group.addSettingCard(
            ReadOnlyInfoCard(
                configItem=cfg.minimaxModel,
                icon=FIF.ROBOT,
                title="模型",
                content="当前使用的 Minimax 模型",
                parent=group,
            )
        )
        group.addSettingCard(
            ReadOnlyInfoCard(
                configItem=cfg.minimaxSpeed,
                icon=FIF.SPEED_OFF,
                title="语速",
                content="当前的语音播放速度",
                parent=group,
            )
        )
        group.addSettingCard(
            ReadOnlyInfoCard(
                configItem=cfg.minimaxVol,
                icon=FIF.VOLUME,
                title="音量",
                content="当前的语音音量",
                parent=group,
            )
        )
        group.addSettingCard(
            ReadOnlyInfoCard(
                configItem=cfg.minimaxPitch,
                icon=FIF.MUSIC,
                title="音调",
                content="当前的语音音调",
                parent=group,
            )
        )
        return group

    def _build_fish_speech_group(self) -> SettingCardGroup:
        """构建 Fish Speech 当前参数分组"""
        group = SettingCardGroup("Fish Speech 当前参数", self.scrollWidget)
        group.addSettingCard(
            ReadOnlyInfoCard(
                configItem=cfg.fishSpeechApiUrl,
                icon=FIF.LINK,
                title="API 地址",
                content="Fish Speech TTS 服务的 API 地址",
                parent=group,
            )
        )
        return group

    def _build_gpt_sovits_group(self) -> SettingCardGroup:
        """构建 GPT-SoVITS 当前参数分组（仅核心 6 项）"""
        group = SettingCardGroup("GPT-SoVITS 当前参数", self.scrollWidget)
        group.addSettingCard(
            ReadOnlyInfoCard(
                configItem=cfg.gptSovitsApiUrl,
                icon=FIF.LINK,
                title="API 地址",
                content="GPT-SoVITS TTS 服务的 API 地址",
                parent=group,
            )
        )
        group.addSettingCard(
            ReadOnlyInfoCard(
                configItem=cfg.gptSovitsRefAudioPath,
                icon=FIF.MUSIC,
                title="参考音频路径",
                content="当前使用的参考音频文件",
                parent=group,
            )
        )
        group.addSettingCard(
            ReadOnlyInfoCard(
                configItem=cfg.gptSovitsRefText,
                icon=FIF.EDIT,
                title="参考文本",
                content="参考音频对应的文本内容",
                parent=group,
            )
        )
        group.addSettingCard(
            ReadOnlyInfoCard(
                configItem=cfg.gptSovitsTopK,
                icon=FIF.TAG,
                title="Top K",
                content="采样时的 Top K 值",
                parent=group,
            )
        )
        group.addSettingCard(
            ReadOnlyInfoCard(
                configItem=cfg.gptSovitsTopP,
                icon=FIF.TAG,
                title="Top P",
                content="采样时的 Top P 值",
                parent=group,
            )
        )
        group.addSettingCard(
            ReadOnlyInfoCard(
                configItem=cfg.gptSovitsTemperature,
                icon=FIF.CARE_RIGHT_SOLID,
                title="采样温度",
                content="当前的采样温度",
                parent=group,
            )
        )
        return group

    def _init_layout(self) -> None:
        """初始化布局"""
        self.title_label.move(36, 30)

        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(36, 10, 36, 10)
        self.expandLayout.addWidget(self.test_card)
        self.expandLayout.addWidget(self.minimaxGroup)
        self.expandLayout.addWidget(self.fishSpeechGroup)
        self.expandLayout.addWidget(self.gptSovitsGroup)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 80, 0, 20)
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)

        self.scrollWidget.setObjectName("scrollWidget")
        self.title_label.setObjectName("titleLabel")

    def _connect_signals(self) -> None:
        """连接信号"""
        self.test_button.clicked.connect(self._on_test_button_clicked)
        cfg.activeTTS.valueChanged.connect(self._on_active_tts_changed)
        cfg.voiceDict.valueChanged.connect(self._refresh_voice_display)

    def _on_active_tts_changed(self, *_: object) -> None:
        """根据当前激活的 TTS 服务切换参数分组的可见性"""
        active = cfg.activeTTS.value
        self.minimaxGroup.setVisible(active == ServiceType.MINIMAX)
        self.fishSpeechGroup.setVisible(active == ServiceType.FISH_SPEECH)
        self.gptSovitsGroup.setVisible(active == ServiceType.GPT_SOVITS)

    def _refresh_voice_display(self, *_: object) -> None:
        """voiceDict 变更时，重新格式化音色显示文本

        音色 ID 没变所以 valueChanged 不会触发，需要手动重算一次。
        """
        self.minimaxVoiceCard.refresh()

    @asyncSlot()
    async def _on_test_button_clicked(self) -> None:
        """测试按钮点击事件"""
        text = self.text_edit.toPlainText()
        if not text:
            return
        try:
            tts_service = get_tts_service()
            audio = await tts_service.text_to_speech(text)
            await audio_player.play_bytes_async(audio)
        except Exception as e:
            logger.exception(f"音频测试失败: {e}")
            InfoBar.error(
                title="测试失败",
                content=str(e),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )
