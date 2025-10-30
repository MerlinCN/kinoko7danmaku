"""设置界面"""

from PySide6.QtWidgets import QWidget
from qfluentwidgets import (
    ExpandLayout,
    FluentIcon as FIF,
    OptionsSettingCard,
    ScrollArea,
    SettingCardGroup,
    SwitchSettingCard,
    TitleLabel,
    qconfig,
    setTheme,
)

from config.qconfig import cfg
from ..components import IntSettingCard, StrSettingCard
from schema.const import SUPPORTED_SERVICES


class SettingsInterface(ScrollArea):
    """设置界面"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.scrollWidget = QWidget()
        self.expandLayout = ExpandLayout(self.scrollWidget)

        # 标题
        self.settingLabel = TitleLabel("设置", self)

        # 个性化设置组
        self.personalGroup = SettingCardGroup("个性化", self.scrollWidget)

        # 主题设置
        self.themeCard = OptionsSettingCard(
            qconfig.themeMode,
            FIF.BRUSH,
            "应用主题",
            "更改应用的外观主题",
            texts=["浅色", "深色", "跟随系统设置"],
            parent=self.personalGroup,
        )

        # B站直播服务设置组
        self.biliGroup = SettingCardGroup("B站设置", self.scrollWidget)

        # 房间号设置
        self.roomIdCard = IntSettingCard(
            configItem=cfg.roomId,
            icon=FIF.CHAT,
            title="房间号",
            content="设置要监控的B站直播间房间号",
            parent=self.biliGroup,
            placeholder="注意是直播间房间号，不是 UID",
        )

        # 礼物阈值设置
        self.giftThresholdCard = IntSettingCard(
            configItem=cfg.giftThreshold,
            icon=FIF.HEART,
            title="礼物阈值（元）",
            content="只播报价值大于等于此阈值的礼物",
            parent=self.biliGroup,
        )

        # 功能开关
        self.normalDanmakuCard = SwitchSettingCard(
            icon=FIF.CHAT,
            title="普通弹幕",
            content="是否播报普通弹幕",
            configItem=cfg.normalDanmakuOn,
            parent=self.biliGroup,
        )

        self.guardCard = SwitchSettingCard(
            icon=FIF.PEOPLE,
            title="舰长购买",
            content="是否播报舰长购买消息",
            configItem=cfg.guardOn,
            parent=self.biliGroup,
        )

        self.superChatCard = SwitchSettingCard(
            icon=FIF.MESSAGE,
            title="醒目留言",
            content="是否播报醒目留言",
            configItem=cfg.superChatOn,
            parent=self.biliGroup,
        )

        self.welcomeCard = SwitchSettingCard(
            icon=FIF.ACCEPT,
            title="启动欢迎语",
            content="启动成功后是否播报欢迎语",
            configItem=cfg.welcomeOn,
            parent=self.biliGroup,
        )

        self.debugCard = SwitchSettingCard(
            icon=FIF.CODE,
            title="调试模式",
            content="开启后显示详细的调试信息",
            configItem=cfg.debug,
            parent=self.biliGroup,
        )

        # TTS 服务设置组
        self.ttsGroup = SettingCardGroup("文字转语音（TTS）设置", self.scrollWidget)

        self.activeTTSCard = OptionsSettingCard(
            configItem=cfg.activeTTS,
            icon=FIF.MICROPHONE,
            title="使用的TTS服务",
            content="设置使用的TTS服务",
            texts=[item.description for item in SUPPORTED_SERVICES.values()],
            parent=self.ttsGroup,
        )
        # Minimax 设置
        self.minimaxApiKeyCard = StrSettingCard(
            configItem=cfg.minimaxApiKey,
            icon=FIF.EDIT,
            title="Minimax API Key",
            content="设置 Minimax TTS 服务的 API 密钥",
            parent=self.ttsGroup,
            placeholder="请输入 API Key",
        )

        self.minimaxVoiceIdCard = StrSettingCard(
            configItem=cfg.minimaxVoiceId,
            icon=FIF.MICROPHONE,
            title="Minimax 音色ID",
            content="设置 Minimax TTS 服务的音色ID",
            parent=self.ttsGroup,
        )

        # Fish Speech 设置
        self.fishSpeechUrlCard = StrSettingCard(
            configItem=cfg.fishSpeechUrl,
            icon=FIF.LINK,
            title="Fish Speech API 地址",
            content="设置 Fish Speech TTS 服务的 API 地址",
            parent=self.ttsGroup,
            placeholder="http://localhost:8080/v1/tts",
        )

        # GPT-SoVITS 设置
        self.gptSovitsUrlCard = StrSettingCard(
            configItem=cfg.gptSovitsUrl,
            icon=FIF.LINK,
            title="GPT-SoVITS API 地址",
            content="设置 GPT-SoVITS TTS 服务的 API 地址",
            parent=self.ttsGroup,
            placeholder="http://localhost:19874",
        )

        # 播放器设置组
        self.playerGroup = SettingCardGroup("音频播放器", self.scrollWidget)

        self.playerDeviceCard = StrSettingCard(
            configItem=cfg.playerDevice,
            icon=FIF.ALBUM,
            title="输出设备",
            content="设置音频输出设备（留空为默认设备）",
            parent=self.playerGroup,
            placeholder="留空使用默认设备",
        )

        # 初始化布局
        self._init_layout()
        self._connect_signals()

    def _connect_signals(self) -> None:
        """连接信号槽"""
        # 连接主题切换信号
        qconfig.themeChanged.connect(setTheme)

    def _init_layout(self) -> None:
        """初始化布局"""
        self.settingLabel.move(36, 30)

        # 添加个性化设置卡片
        self.personalGroup.addSettingCard(self.themeCard)

        # 添加 B站服务设置卡片
        self.biliGroup.addSettingCard(self.roomIdCard)
        self.biliGroup.addSettingCard(self.giftThresholdCard)
        self.biliGroup.addSettingCard(self.normalDanmakuCard)
        self.biliGroup.addSettingCard(self.guardCard)
        self.biliGroup.addSettingCard(self.superChatCard)
        self.biliGroup.addSettingCard(self.welcomeCard)
        self.biliGroup.addSettingCard(self.debugCard)

        # 添加 TTS 服务设置卡片
        self.ttsGroup.addSettingCard(self.activeTTSCard)
        self.ttsGroup.addSettingCard(self.minimaxApiKeyCard)
        self.ttsGroup.addSettingCard(self.minimaxVoiceIdCard)
        self.ttsGroup.addSettingCard(self.fishSpeechUrlCard)
        self.ttsGroup.addSettingCard(self.gptSovitsUrlCard)

        # 添加播放器设置卡片
        self.playerGroup.addSettingCard(self.playerDeviceCard)

        # 设置展开布局
        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(36, 10, 36, 0)
        self.expandLayout.addWidget(self.personalGroup)
        self.expandLayout.addWidget(self.biliGroup)
        self.expandLayout.addWidget(self.ttsGroup)
        self.expandLayout.addWidget(self.playerGroup)

        # 设置滚动区域
        self.setHorizontalScrollBarPolicy(
            __import__(
                "PySide6.QtCore", fromlist=["Qt"]
            ).Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setViewportMargins(0, 80, 0, 20)
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)

        # 设置对象名称
        self.scrollWidget.setObjectName("scrollWidget")
        self.settingLabel.setObjectName("settingLabel")
