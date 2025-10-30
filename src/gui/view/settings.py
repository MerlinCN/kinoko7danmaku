"""设置界面"""

from PySide6.QtWidgets import QWidget
from qfluentwidgets import (
    ExpandLayout,
    FluentIcon as FIF,
    ScrollArea,
    SettingCardGroup,
    SwitchSettingCard,
    ComboBoxSettingCard,
    TitleLabel,
    qconfig,
    setTheme,
)

from core.const import (
    GPT_SOVITS_LANGUAGES,
    GPT_SOVITS_TEXT_SPLIT_METHODS,
    MINIMAX_MODELS,
    SUPPORTED_SERVICES,
)
from core.qconfig import cfg
from ..components import FloatRangeSettingCard, IntSettingCard, StrSettingCard


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
        self.themeCard = ComboBoxSettingCard(
            configItem=qconfig.themeMode,
            icon=FIF.BRUSH,
            title="应用主题",
            content="更改应用的外观主题",
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
            placeholder="注意是直播间房间号",
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

        self.giftOnTextCard = StrSettingCard(
            configItem=cfg.giftOnText,
            icon=FIF.HEART,
            title="礼物触发文本模板",
            content="礼物消息的文本模板（支持变量: {user_name}, {gift_num}, {gift_name}）",
            parent=self.biliGroup,
            placeholder='"{user_name}" 赠送了{gift_num}个{gift_name}',
        )

        self.danmakuOnTextCard = StrSettingCard(
            configItem=cfg.danmakuOnText,
            icon=FIF.CHAT,
            title="弹幕触发文本模板",
            content="弹幕消息的文本模板（支持变量: {user_name}, {message}）",
            parent=self.biliGroup,
            placeholder='"{user_name}"说:"{message}"',
        )

        self.guardOnTextCard = StrSettingCard(
            configItem=cfg.guardOnText,
            icon=FIF.PEOPLE,
            title="舰长触发文本模板",
            content="舰长购买的文本模板（支持变量: {user_name}, {guard_name}）",
            parent=self.biliGroup,
            placeholder='感谢 "{user_name}" 赠送的{guard_name}',
        )

        self.superChatOnTextCard = StrSettingCard(
            configItem=cfg.superChatOnText,
            icon=FIF.MESSAGE,
            title="醒目留言触发文本模板",
            content="醒目留言的文本模板（支持变量: {user_name}, {message}）",
            parent=self.biliGroup,
            placeholder='"{user_name}" 发送了一条醒目留言,他说"{message}"',
        )

        # TTS 服务通用设置组
        self.ttsGroup = SettingCardGroup("文字转语音（TTS）设置", self.scrollWidget)

        self.activeTTSCard = ComboBoxSettingCard(
            configItem=cfg.activeTTS,
            icon=FIF.MICROPHONE,
            title="使用的TTS服务",
            content="设置使用的TTS服务",
            texts=[item.description for item in SUPPORTED_SERVICES.values()],
            parent=self.ttsGroup,
        )

        # Minimax 服务设置组
        self.minimaxGroup = SettingCardGroup("Minimax 设置", self.scrollWidget)

        self.minimaxApiUrlCard = StrSettingCard(
            configItem=cfg.minimaxApiUrl,
            icon=FIF.LINK,
            title="API 地址",
            content="设置 Minimax TTS 服务的 API 地址",
            parent=self.minimaxGroup,
        )

        self.minimaxApiKeyCard = StrSettingCard(
            configItem=cfg.minimaxApiKey,
            icon=FIF.EDIT,
            title="API Key",
            content="设置 Minimax TTS 服务的 API 密钥",
            parent=self.minimaxGroup,
            placeholder="请输入 API Key",
        )

        self.minimaxVoiceIdCard = StrSettingCard(
            configItem=cfg.minimaxVoiceId,
            icon=FIF.MICROPHONE,
            title="音色 ID",
            content="设置 Minimax TTS 服务的音色 ID",
            parent=self.minimaxGroup,
        )

        self.minimaxModelCard = ComboBoxSettingCard(
            configItem=cfg.minimaxModel,
            icon=FIF.ROBOT,
            title="模型",
            content="设置 Minimax TTS 服务的模型",
            texts=MINIMAX_MODELS,
            parent=self.minimaxGroup,
        )

        self.minimaxSpeedCard = FloatRangeSettingCard(
            configItem=cfg.minimaxSpeed,
            icon=FIF.SPEED_OFF,
            title="语速",
            content=f"调整语音播放速度（{cfg.minimaxSpeed.range[0]}-{cfg.minimaxSpeed.range[1]}）",
            step=0.1,
            decimals=1,
            parent=self.minimaxGroup,
        )

        self.minimaxVolCard = FloatRangeSettingCard(
            configItem=cfg.minimaxVol,
            icon=FIF.VOLUME,
            title="音量",
            content=f"调整语音音量（{cfg.minimaxVol.range[0]}-{cfg.minimaxVol.range[1]}）",
            step=0.1,
            decimals=1,
            parent=self.minimaxGroup,
        )

        self.minimaxPitchCard = FloatRangeSettingCard(
            configItem=cfg.minimaxPitch,
            icon=FIF.MUSIC,
            title="音调",
            content=f"调整语音音调（{cfg.minimaxPitch.range[0]}-{cfg.minimaxPitch.range[1]}）",
            step=1,
            decimals=0,
            parent=self.minimaxGroup,
        )

        # Fish Speech 服务设置组
        self.fishSpeechGroup = SettingCardGroup("Fish Speech 设置", self.scrollWidget)

        self.fishSpeechApiUrlCard = StrSettingCard(
            configItem=cfg.fishSpeechApiUrl,
            icon=FIF.LINK,
            title="API 地址",
            content="设置 Fish Speech TTS 服务的 API 地址",
            parent=self.fishSpeechGroup,
            placeholder="http://localhost:8080/v1/tts",
        )

        # GPT-SoVITS 服务设置组
        self.gptSovitsGroup = SettingCardGroup("GPT-SoVITS 设置", self.scrollWidget)

        self.gptSovitsApiUrlCard = StrSettingCard(
            configItem=cfg.gptSovitsApiUrl,
            icon=FIF.LINK,
            title="API 地址",
            content="设置 GPT-SoVITS TTS 服务的 API 地址",
            parent=self.gptSovitsGroup,
            placeholder="http://localhost:19874",
        )

        self.gptSovitsSovitsModelCard = StrSettingCard(
            configItem=cfg.gptSovitsSovitsModel,
            icon=FIF.DOCUMENT,
            title="SoVITS 模型权重",
            content="设置 SoVITS 模型权重文件路径",
            parent=self.gptSovitsGroup,
            placeholder="模型文件路径",
        )

        self.gptSovitsGptModelCard = StrSettingCard(
            configItem=cfg.gptSovitsGptModel,
            icon=FIF.DOCUMENT,
            title="GPT 模型权重",
            content="设置 GPT 模型权重文件路径",
            parent=self.gptSovitsGroup,
            placeholder="模型文件路径",
        )

        self.gptSovitsTextLangCard = ComboBoxSettingCard(
            configItem=cfg.gptSovitsTextLang,
            icon=FIF.LANGUAGE,
            title="文本语言",
            content="设置文本语言",
            texts=GPT_SOVITS_LANGUAGES,
            parent=self.gptSovitsGroup,
        )

        self.gptSovitsRefAudioPathCard = StrSettingCard(
            configItem=cfg.gptSovitsRefAudioPath,
            icon=FIF.MUSIC,
            title="参考音频路径",
            content="设置参考音频文件路径",
            parent=self.gptSovitsGroup,
            placeholder="音频文件路径",
        )

        self.gptSovitsRefTextCard = StrSettingCard(
            configItem=cfg.gptSovitsRefText,
            icon=FIF.EDIT,
            title="参考文本",
            content="设置参考音频对应的文本内容",
            parent=self.gptSovitsGroup,
            placeholder="参考文本内容",
        )

        self.gptSovitsRefTextLangCard = ComboBoxSettingCard(
            configItem=cfg.gptSovitsRefTextLang,
            icon=FIF.LANGUAGE,
            title="参考文本语言",
            content="设置参考文本语言",
            texts=GPT_SOVITS_LANGUAGES,
            parent=self.gptSovitsGroup,
        )

        self.gptSovitsTopKCard = IntSettingCard(
            configItem=cfg.gptSovitsTopK,
            icon=FIF.TAG,
            title="Top K",
            content="设置采样时的 Top K 值",
            parent=self.gptSovitsGroup,
        )

        self.gptSovitsTopPCard = FloatRangeSettingCard(
            configItem=cfg.gptSovitsTopP,
            icon=FIF.TAG,
            title="Top P",
            content=f"设置采样时的 Top P 值（{cfg.gptSovitsTopP.range[0]}-{cfg.gptSovitsTopP.range[1]}）",
            step=0.1,
            decimals=1,
            parent=self.gptSovitsGroup,
        )

        self.gptSovitsTemperatureCard = FloatRangeSettingCard(
            configItem=cfg.gptSovitsTemperature,
            icon=FIF.CARE_RIGHT_SOLID,
            title="采样温度",
            content=f"设置采样温度（{cfg.gptSovitsTemperature.range[0]}-{cfg.gptSovitsTemperature.range[1]}）",
            step=0.1,
            decimals=1,
            parent=self.gptSovitsGroup,
        )

        self.gptSovitsTextSplitMethodCard = ComboBoxSettingCard(
            configItem=cfg.gptSovitsTextSplitMethod,
            icon=FIF.CUT,
            title="文本切分方式",
            content="设置文本切分方式",
            texts=GPT_SOVITS_TEXT_SPLIT_METHODS,
            parent=self.gptSovitsGroup,
        )

        self.gptSovitsSpeedFactorCard = FloatRangeSettingCard(
            configItem=cfg.gptSovitsSpeedFactor,
            icon=FIF.SPEED_OFF,
            title="语速调整",
            content=f"设置语速调整系数（{cfg.gptSovitsSpeedFactor.range[0]}-{cfg.gptSovitsSpeedFactor.range[1]}）",
            step=0.1,
            decimals=1,
            parent=self.gptSovitsGroup,
        )

        self.gptSovitsRefTextFreeCard = SwitchSettingCard(
            icon=FIF.CHECKBOX,
            title="无参考文本模式",
            content="是否启用无参考文本模式",
            configItem=cfg.gptSovitsRefTextFree,
            parent=self.gptSovitsGroup,
        )

        self.gptSovitsSampleStepsCard = IntSettingCard(
            configItem=cfg.gptSovitsSampleSteps,
            icon=FIF.IOT,
            title="采样步数",
            content="设置采样步数",
            parent=self.gptSovitsGroup,
        )

        self.gptSovitsSuperSamplingCard = SwitchSettingCard(
            icon=FIF.ZOOM,
            title="超采样",
            content="是否启用超采样",
            configItem=cfg.gptSovitsSuperSampling,
            parent=self.gptSovitsGroup,
        )

        self.gptSovitsPauseSecondsCard = FloatRangeSettingCard(
            configItem=cfg.gptSovitsPauseSeconds,
            icon=FIF.PAUSE,
            title="句间停顿秒数",
            content=f"设置句间停顿时长（{cfg.gptSovitsPauseSeconds.range[0]}-{cfg.gptSovitsPauseSeconds.range[1]}秒）",
            step=0.1,
            decimals=1,
            parent=self.gptSovitsGroup,
        )

        # 播放器设置组
        self.playerGroup = SettingCardGroup("音频设置", self.scrollWidget)

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
        self.biliGroup.addSettingCard(self.giftOnTextCard)
        self.biliGroup.addSettingCard(self.danmakuOnTextCard)
        self.biliGroup.addSettingCard(self.guardOnTextCard)
        self.biliGroup.addSettingCard(self.superChatOnTextCard)

        # 添加 TTS 服务通用设置卡片
        self.ttsGroup.addSettingCard(self.activeTTSCard)

        # 添加 Minimax 服务设置卡片
        self.minimaxGroup.addSettingCard(self.minimaxApiUrlCard)
        self.minimaxGroup.addSettingCard(self.minimaxApiKeyCard)
        self.minimaxGroup.addSettingCard(self.minimaxVoiceIdCard)
        self.minimaxGroup.addSettingCard(self.minimaxModelCard)
        self.minimaxGroup.addSettingCard(self.minimaxSpeedCard)
        self.minimaxGroup.addSettingCard(self.minimaxVolCard)
        self.minimaxGroup.addSettingCard(self.minimaxPitchCard)

        # 添加 Fish Speech 服务设置卡片
        self.fishSpeechGroup.addSettingCard(self.fishSpeechApiUrlCard)

        # 添加 GPT-SoVITS 服务设置卡片
        self.gptSovitsGroup.addSettingCard(self.gptSovitsApiUrlCard)
        self.gptSovitsGroup.addSettingCard(self.gptSovitsSovitsModelCard)
        self.gptSovitsGroup.addSettingCard(self.gptSovitsGptModelCard)
        self.gptSovitsGroup.addSettingCard(self.gptSovitsTextLangCard)
        self.gptSovitsGroup.addSettingCard(self.gptSovitsRefAudioPathCard)
        self.gptSovitsGroup.addSettingCard(self.gptSovitsRefTextCard)
        self.gptSovitsGroup.addSettingCard(self.gptSovitsRefTextLangCard)
        self.gptSovitsGroup.addSettingCard(self.gptSovitsTopKCard)
        self.gptSovitsGroup.addSettingCard(self.gptSovitsTopPCard)
        self.gptSovitsGroup.addSettingCard(self.gptSovitsTemperatureCard)
        self.gptSovitsGroup.addSettingCard(self.gptSovitsTextSplitMethodCard)
        self.gptSovitsGroup.addSettingCard(self.gptSovitsSpeedFactorCard)
        self.gptSovitsGroup.addSettingCard(self.gptSovitsRefTextFreeCard)
        self.gptSovitsGroup.addSettingCard(self.gptSovitsSampleStepsCard)
        self.gptSovitsGroup.addSettingCard(self.gptSovitsSuperSamplingCard)
        self.gptSovitsGroup.addSettingCard(self.gptSovitsPauseSecondsCard)

        # 添加播放器设置卡片
        self.playerGroup.addSettingCard(self.playerDeviceCard)

        # 设置展开布局
        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(36, 10, 36, 0)
        self.expandLayout.addWidget(self.personalGroup)
        self.expandLayout.addWidget(self.biliGroup)
        self.expandLayout.addWidget(self.playerGroup)
        self.expandLayout.addWidget(self.ttsGroup)
        self.expandLayout.addWidget(self.minimaxGroup)
        self.expandLayout.addWidget(self.fishSpeechGroup)
        self.expandLayout.addWidget(self.gptSovitsGroup)

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
