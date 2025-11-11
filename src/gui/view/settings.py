"""设置界面"""

import asyncio

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget
from qasync import asyncSlot
from qfluentwidgets import (
    ComboBoxSettingCard,
    ExpandGroupSettingCard,
    ExpandLayout,
    ScrollArea,
    SettingCardGroup,
    StateToolTip,
    SwitchSettingCard,
    TitleLabel,
    qconfig,
    setTheme,
)
from qfluentwidgets import (
    FluentIcon as FIF,
)

from core.const import (
    GPT_SOVITS_LANGUAGES,
    GPT_SOVITS_TEXT_SPLIT_METHODS,
    MINIMAX_ERROR_VOICE_ID,
    MINIMAX_MODELS,
    SUPPORTED_SERVICES,
)
from core.player import audio_player
from core.qconfig import cfg, get_voices

from ..components import FloatRangeSettingCard, IntSettingCard, StrSettingCard
from ..components.alias_dict_card import AliasDictCard
from ..components.dict_edit_card import DictEditCard


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

        self.freeGiftOnCard = SwitchSettingCard(
            icon=FIF.HEART,
            title="免费礼物",
            content="是否播报免费礼物",
            configItem=cfg.freeGiftOn,
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

        # 礼物合并设置卡片（可展开）
        self.giftMergeCard = ExpandGroupSettingCard(
            icon=FIF.TRANSPARENT,
            title="礼物合并设置",
            content="配置礼物合并的相关参数",
            parent=self.biliGroup,
        )

        # 礼物合并开关
        self.giftMergeOnCard = SwitchSettingCard(
            icon=FIF.SYNC,
            title="启用礼物合并",
            content="合并短时间内相同用户的相同礼物",
            configItem=cfg.giftMergeOn,
            parent=self.giftMergeCard,
        )

        # 初始窗口时间
        self.giftMergeWindowInitialCard = FloatRangeSettingCard(
            configItem=cfg.giftMergeWindowInitial,
            icon=FIF.DATE_TIME,
            title="初始窗口时间（秒）",
            content=f"首次收到礼物时的等待时间（{cfg.giftMergeWindowInitial.range[0]}-{cfg.giftMergeWindowInitial.range[1]}秒）",
            step=0.1,
            decimals=1,
            parent=self.giftMergeCard,
        )

        # 窗口时间递增
        self.giftMergeWindowIncrementCard = FloatRangeSettingCard(
            configItem=cfg.giftMergeWindowIncrement,
            icon=FIF.UP,
            title="窗口时间递增（秒）",
            content=f"每次收到新礼物时窗口时间增加的值（{cfg.giftMergeWindowIncrement.range[0]}-{cfg.giftMergeWindowIncrement.range[1]}秒）",
            step=0.1,
            decimals=1,
            parent=self.giftMergeCard,
        )

        # 最大窗口时间
        self.giftMergeWindowCard = FloatRangeSettingCard(
            configItem=cfg.giftMergeWindow,
            icon=FIF.STOP_WATCH,
            title="最大窗口时间（秒）",
            content=f"窗口时间的上限，也是强制播报的最长等待时间（{cfg.giftMergeWindow.range[0]}-{cfg.giftMergeWindow.range[1]}秒）",
            step=0.5,
            decimals=1,
            parent=self.giftMergeCard,
        )

        # 将子卡片添加到展开卡片中
        self.giftMergeCard.addGroupWidget(self.giftMergeOnCard)
        self.giftMergeCard.addGroupWidget(self.giftMergeWindowInitialCard)
        self.giftMergeCard.addGroupWidget(self.giftMergeWindowIncrementCard)
        self.giftMergeCard.addGroupWidget(self.giftMergeWindowCard)

        self.aliasDictCard = AliasDictCard(self.biliGroup)

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

        self.minimaxApiKeyCard = StrSettingCard(
            configItem=cfg.minimaxApiKey,
            icon=FIF.EDIT,
            title="API Key",
            content="设置 Minimax TTS 服务的 API 密钥",
            parent=self.minimaxGroup,
            placeholder="请输入 API Key",
        )

        self.voiceDictCard = DictEditCard(
            config_item=cfg.voiceDict,
            icon=FIF.MICROPHONE,
            title="音色字典",
            content="设置音色 ID 与显示名称的映射关系",
            key_label="音色ID",
            value_label="显示名称",
            key_placeholder="输入音色ID",
            value_placeholder="输入显示名称",
            parent=self.minimaxGroup,
        )
        self.minimaxVoiceIdCard = ComboBoxSettingCard(
            configItem=cfg.minimaxVoiceId,
            icon=FIF.MICROPHONE,
            title="音色 ID",
            content="设置 Minimax TTS 服务的音色 ID",
            texts=list(cfg.voiceDict.value.values()),
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

        self.playerDeviceCard = ComboBoxSettingCard(
            configItem=cfg.playerDevice,
            icon=FIF.ALBUM,
            title="输出设备",
            content="设置音频输出设备",
            parent=self.playerGroup,
            texts=[device.name for device in audio_player.get_output_devices()],
        )

        # 初始化布局
        self._init_layout()
        self._connect_signals()

    def _connect_signals(self) -> None:
        """连接信号槽"""
        # 连接主题切换信号
        qconfig.themeChanged.connect(setTheme)
        cfg.playerDevice.valueChanged.connect(self._on_output_device_changed)
        # 连接 voiceDict 变更信号
        cfg.voiceDict.valueChanged.connect(self._on_voice_dict_changed)

    @asyncSlot()
    async def _on_minimax_api_key_changed_async(self) -> None:
        """API Key 改变时更新音色列表（异步，不阻塞界面）"""
        toast = StateToolTip("请稍候", "正在获取音色列表...", self)
        toast.show()
        if not cfg.minimaxApiKey.value:
            voices = [MINIMAX_ERROR_VOICE_ID]
            cfg.minimaxVoiceId.validator.options = voices
            cfg.minimaxVoiceId.value = MINIMAX_ERROR_VOICE_ID
            self._update_voice_options(voices, MINIMAX_ERROR_VOICE_ID)
            return

        # 在线程池中执行网络请求（不阻塞事件循环）
        voices = await asyncio.to_thread(get_voices, cfg.minimaxApiKey.value)
        if not voices:
            voices = [MINIMAX_ERROR_VOICE_ID]

        cfg.minimaxVoiceId.validator.options = voices

        # 如果当前值不在新列表中，使用第一个选项
        value = voices[0] if voices else MINIMAX_ERROR_VOICE_ID
        if cfg.minimaxVoiceId.value in voices:
            value = cfg.minimaxVoiceId.value

        cfg.minimaxVoiceId.value = value
        self._update_voice_options(voices, value)
        toast.setTitle("完成")
        toast.setContent("音色列表获取完成")
        toast.setState(True)
        toast.close()

    def _on_output_device_changed(self) -> None:
        audio_player.set_output_device(cfg.playerDevice.value)

    def _on_voice_dict_changed(self) -> None:
        """voiceDict 改变时更新音色选择卡片的选项

        从 voiceDict 获取最新的音色列表并更新下拉框。
        """
        voice_dict = cfg.voiceDict.value
        if not voice_dict:
            return

        # 获取音色 ID 列表（键）和显示名称列表（值）
        voice_ids = list(voice_dict.keys())

        # 更新验证器的选项
        cfg.minimaxVoiceId.validator.options = voice_ids
        # 如果当前值不在新列表中，使用第一个选项
        current_value = cfg.minimaxVoiceId.value
        if current_value not in voice_ids:
            cfg.minimaxVoiceId.value = voice_ids[0]

        self.minimaxVoiceIdCard.comboBox.clear()

        # 更新选项到文本的映射（音色 ID -> 显示名称）
        self.minimaxVoiceIdCard.optionToText = voice_dict

        # 重新添加选项（显示名称，但 userData 存储音色 ID）
        for voice_id, name in voice_dict.items():
            self.minimaxVoiceIdCard.comboBox.addItem(name, userData=voice_id)

        # 设置选中项
        self.minimaxVoiceIdCard.setValue(cfg.minimaxVoiceId.value)

    def _init_layout(self) -> None:
        """初始化布局"""
        self.settingLabel.move(36, 30)

        # 添加个性化设置卡片
        self.personalGroup.addSettingCard(self.themeCard)

        # 添加 B站服务设置卡片
        self.biliGroup.addSettingCard(self.roomIdCard)
        self.biliGroup.addSettingCard(self.giftThresholdCard)
        self.biliGroup.addSettingCard(self.freeGiftOnCard)
        self.biliGroup.addSettingCard(self.normalDanmakuCard)
        self.biliGroup.addSettingCard(self.guardCard)
        self.biliGroup.addSettingCard(self.superChatCard)
        self.biliGroup.addSettingCard(self.debugCard)
        self.biliGroup.addSettingCard(self.giftOnTextCard)
        self.biliGroup.addSettingCard(self.danmakuOnTextCard)
        self.biliGroup.addSettingCard(self.guardOnTextCard)
        self.biliGroup.addSettingCard(self.superChatOnTextCard)
        self.biliGroup.addSettingCard(self.giftMergeCard)
        self.biliGroup.addSettingCard(self.aliasDictCard)

        # 添加 TTS 服务通用设置卡片
        self.ttsGroup.addSettingCard(self.activeTTSCard)

        # 添加 Minimax 服务设置卡片
        self.minimaxGroup.addSettingCard(self.minimaxApiKeyCard)
        self.minimaxGroup.addSettingCard(self.voiceDictCard)
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
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 80, 0, 20)
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)

        # 设置对象名称
        self.scrollWidget.setObjectName("scrollWidget")
        self.settingLabel.setObjectName("settingLabel")
