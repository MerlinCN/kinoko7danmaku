"""MiniMax 音色列表界面"""

from loguru import logger
from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qasync import asyncSlot
from qfluentwidgets import (
    Action,
    BodyLabel,
    CaptionLabel,
    CardWidget,
    ComboBox,
    FlowLayout,
    InfoBar,
    InfoBarPosition,
    RoundMenu,
    ScrollArea,
    Slider,
    StateToolTip,
    SubtitleLabel,
    TextEdit,
    TitleLabel,
    ToolButton,
    TransparentToolButton,
)
from qfluentwidgets import FluentIcon as FIF

from core.const import MINIMAX_MODELS
from core.player import audio_player
from core.qconfig import cfg
from models.minimax import VoiceItem
from tts_service.minimax import MinimaxService


class VoiceCard(CardWidget):
    """音色卡片"""

    voiceSelected = Signal(str)  # 选择音色时发出音色 ID

    def __init__(
        self,
        voice_id: str,
        voice_name: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """初始化音色卡片

        Args:
            voice_id: 音色 ID
            voice_name: 音色名称，如果为 None 则使用 voice_id
            parent: 父窗口
        """
        super().__init__(parent)
        self.voice_id = voice_id
        self.voice_name = voice_name or voice_id
        self._is_selected = False

        self._init_ui()

    def _init_ui(self) -> None:
        """初始化 UI"""
        self.hBoxLayout = QHBoxLayout(self)
        self.vBoxLayout = QVBoxLayout()

        # 音色名称
        self.titleLabel = BodyLabel(self.voice_name, self)
        self.titleLabel.setFont(self.titleLabel.font())

        # 音色 ID（小字）
        self.idLabel = CaptionLabel(self.voice_id, self)
        self.idLabel.setTextColor("#606060", "#d2d2d2")

        # 使用按钮
        self.useButton = ToolButton(FIF.PLAY, self)
        self.useButton.setFixedSize(32, 32)
        self.useButton.setToolTip("试听")

        # 更多按钮
        self.moreButton = TransparentToolButton(FIF.MORE, self)
        self.moreButton.setFixedSize(32, 32)
        self.moreButton.clicked.connect(self._on_more_clicked)

        # 布局
        self.setFixedHeight(73)
        self.hBoxLayout.setContentsMargins(20, 11, 11, 11)
        self.hBoxLayout.setSpacing(15)

        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(0)
        self.vBoxLayout.addWidget(self.titleLabel, 0, Qt.AlignmentFlag.AlignVCenter)
        self.vBoxLayout.addWidget(self.idLabel, 0, Qt.AlignmentFlag.AlignVCenter)
        self.vBoxLayout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.hBoxLayout.addLayout(self.vBoxLayout)
        self.hBoxLayout.addStretch(1)
        self.hBoxLayout.addWidget(self.useButton, 0, Qt.AlignmentFlag.AlignRight)
        self.hBoxLayout.addWidget(self.moreButton, 0, Qt.AlignmentFlag.AlignRight)

    def _on_more_clicked(self) -> None:
        """更多按钮点击事件"""
        menu = RoundMenu(parent=self)
        menu.addAction(Action(FIF.COPY, "复制音色 ID", self))
        menu.addAction(Action(FIF.INFO, "查看详情", self))

        x = (self.moreButton.width() - menu.width()) // 2 + 10
        pos = self.moreButton.mapToGlobal(QPoint(x, self.moreButton.height()))
        menu.exec(pos)

    def mousePressEvent(self, event) -> None:
        """鼠标点击事件

        Args:
            event: 鼠标事件
        """
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.voiceSelected.emit(self.voice_id)

    def set_selected(self, selected: bool) -> None:
        """设置选中状态

        Args:
            selected: 是否选中
        """
        self._is_selected = selected
        if selected:
            self.setStyleSheet("VoiceCard { border: 2px solid rgb(0, 120, 212); }")
        else:
            self.setStyleSheet("")


class MinimaxVoiceListInterface(QWidget):
    """MiniMax 音色列表界面"""

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化 MiniMax 音色列表界面

        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        self._voices: list[VoiceItem] = []
        self._tts_service = MinimaxService()
        self._current_voice_id: str | None = None
        self._voice_cards: dict[str, VoiceCard] = {}  # voice_id -> VoiceCard

        # 临时参数（独立于全局配置）
        self._temp_model: str = cfg.minimaxModel.value
        self._temp_speed: float = 1.0
        self._temp_vol: float = 1.0
        self._temp_pitch: int = 0

        self._is_playing = False
        self._is_loaded = False  # 是否已加载过音色列表

        self._init_ui()

    def _init_ui(self) -> None:
        """初始化界面布局"""
        # 主容器布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(36, 36, 36, 36)
        main_layout.setSpacing(20)

        # 标题
        self.title_label = TitleLabel("音色列表")
        main_layout.addWidget(self.title_label)

        # 内容区：水平分栏
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # === 左侧面板：音色卡片网格 ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        # 左侧标题
        left_title = SubtitleLabel("可用音色")
        left_layout.addWidget(left_title)

        # 滚动区域
        self.scroll_area = ScrollArea()
        self.scroll_area.setWidgetResizable(True)

        # 音色卡片容器
        self.voice_container = QWidget()
        self.voice_flow_layout = FlowLayout(self.voice_container, needAni=True)
        self.voice_flow_layout.setContentsMargins(0, 0, 0, 0)
        self.voice_flow_layout.setHorizontalSpacing(10)
        self.voice_flow_layout.setVerticalSpacing(10)

        self.scroll_area.setWidget(self.voice_container)
        left_layout.addWidget(self.scroll_area)

        content_layout.addWidget(left_panel, 1)

        # === 右侧布局 ===
        right_layout = QVBoxLayout()
        right_layout.setSpacing(20)

        # --- 测试卡片 ---
        self.test_card = CardWidget()
        test_card_layout = QVBoxLayout(self.test_card)
        test_card_layout.setContentsMargins(20, 20, 20, 20)
        test_card_layout.setSpacing(12)

        test_title = SubtitleLabel("音色测试")
        test_card_layout.addWidget(test_title)

        # 文本输入框
        self.text_edit = TextEdit()
        self.text_edit.setPlaceholderText("输入测试文本...")
        self.text_edit.setMinimumHeight(120)
        test_card_layout.addWidget(self.text_edit)

        # 播放按钮（右对齐）
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.play_button = ToolButton(FIF.PLAY)
        self.play_button.clicked.connect(self._on_play_clicked)
        button_layout.addWidget(self.play_button)
        test_card_layout.addLayout(button_layout)

        right_layout.addWidget(self.test_card)

        # --- 参数卡片 ---
        self.param_card = CardWidget()
        param_card_layout = QVBoxLayout(self.param_card)
        param_card_layout.setContentsMargins(20, 20, 20, 20)
        param_card_layout.setSpacing(16)

        param_title = SubtitleLabel("音色参数")
        param_card_layout.addWidget(param_title)

        # 模型选择
        model_layout = QHBoxLayout()
        model_label = QLabel("模型")
        model_label.setFixedWidth(80)
        self.model_combo = ComboBox()
        self.model_combo.addItems(MINIMAX_MODELS)
        self.model_combo.setCurrentText(self._temp_model)
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_combo)
        param_card_layout.addLayout(model_layout)

        # 语速滑块
        self._create_slider_row(
            param_card_layout, "语速", 0.5, 2.0, 1.0, self._on_speed_changed
        )

        # 音量滑块
        self._create_slider_row(
            param_card_layout, "音量", 0.0, 2.0, 1.0, self._on_vol_changed
        )

        # 音调滑块
        self._create_slider_row(
            param_card_layout, "音调", -12, 12, 0, self._on_pitch_changed, is_int=True
        )

        right_layout.addWidget(self.param_card)
        right_layout.addStretch()

        content_layout.addLayout(right_layout, 1)  # 右侧占 1 份

        main_layout.addLayout(content_layout, 1)

    def showEvent(self, event) -> None:
        """界面显示事件

        Args:
            event: 显示事件
        """
        super().showEvent(event)
        # 首次显示时加载音色列表
        if not self._is_loaded:
            QTimer.singleShot(0, self._load_voice_list)

    def _create_slider_row(
        self,
        parent_layout: QVBoxLayout,
        label_text: str,
        min_val: float,
        max_val: float,
        default_val: float,
        callback,
        is_int: bool = False,
    ) -> None:
        """创建滑块行

        Args:
            parent_layout: 父布局
            label_text: 标签文本
            min_val: 最小值
            max_val: 最大值
            default_val: 默认值
            callback: 值变化回调
            is_int: 是否为整数滑块
        """
        row_layout = QHBoxLayout()
        label = QLabel(label_text)
        label.setFixedWidth(80)

        slider = Slider(Qt.Orientation.Horizontal)
        if is_int:
            slider.setRange(int(min_val), int(max_val))
            slider.setValue(int(default_val))
        else:
            # 浮点数：转换为整数范围（精度 0.1）
            slider.setRange(int(min_val * 10), int(max_val * 10))
            slider.setValue(int(default_val * 10))

        value_label = QLabel(str(default_val))
        value_label.setFixedWidth(50)
        value_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        # 连接信号
        if is_int:
            slider.valueChanged.connect(
                lambda v: (value_label.setText(str(v)), callback(v))
            )
        else:
            slider.valueChanged.connect(
                lambda v: (
                    value_label.setText(f"{v / 10:.1f}"),
                    callback(v / 10),
                )
            )

        row_layout.addWidget(label)
        row_layout.addWidget(slider, 1)
        row_layout.addWidget(value_label)
        parent_layout.addLayout(row_layout)

        # 保存引用（用于后续访问）
        if label_text == "语速":
            self.speed_slider = slider
            self.speed_label = value_label
        elif label_text == "音量":
            self.vol_slider = slider
            self.vol_label = value_label
        elif label_text == "音调":
            self.pitch_slider = slider
            self.pitch_label = value_label

    @asyncSlot()
    async def _load_voice_list(self) -> None:
        """异步加载音色列表"""
        # 检查 API Key
        if not cfg.minimaxApiKey.value:
            self._show_empty_state("请先在设置中配置 MiniMax API Key")
            return

        # 显示加载状态
        state_tooltip = StateToolTip("正在加载", "加载音色列表中...", self.window())
        state_tooltip.move(state_tooltip.getSuitablePos())
        state_tooltip.show()

        try:
            response = await self._tts_service.get_voice_list()
            self._voices = response.voice_cloning
            self._update_voice_list()
            state_tooltip.setState(True)
            state_tooltip.setTitle("加载成功")
            self._is_loaded = True
            logger.info(f"成功加载 {len(self._voices)} 个音色")
        except ValueError as e:
            logger.error(f"加载音色列表失败: {e}")
            state_tooltip.setState(False)
            state_tooltip.setTitle("加载失败")
            state_tooltip.setContent(str(e))
            self._show_empty_state(f"加载失败: {e}")
        except Exception as e:
            logger.exception(f"加载音色列表失败: {e}")
            state_tooltip.setState(False)
            state_tooltip.setTitle("加载失败")
            state_tooltip.setContent("网络请求失败，请检查网络连接")
            self._show_empty_state("加载失败，请检查网络连接和 API Key 是否正确")

    def _update_voice_list(self) -> None:
        """更新音色列表显示"""
        # 清空现有卡片
        for card in self._voice_cards.values():
            self.voice_flow_layout.removeWidget(card)
            card.deleteLater()
        self._voice_cards.clear()

        card_width = 500

        # 创建新卡片
        for voice in self._voices:
            card = VoiceCard(voice.voice_id, voice.voice_name, self.voice_container)
            card.setFixedWidth(card_width)
            card.voiceSelected.connect(self._on_voice_card_clicked)
            card.useButton.clicked.connect(
                lambda _, vid=voice.voice_id: self._on_voice_card_clicked(vid)
            )

            self._voice_cards[voice.voice_id] = card
            self.voice_flow_layout.addWidget(card)

    def _show_empty_state(self, message: str) -> None:
        """显示空状态提示

        Args:
            message: 提示信息
        """
        # 清空现有卡片
        for card in self._voice_cards.values():
            self.voice_flow_layout.removeWidget(card)
            card.deleteLater()
        self._voice_cards.clear()

        # 显示空状态消息卡片
        empty_card = CardWidget(self.voice_container)
        empty_layout = QVBoxLayout(empty_card)
        empty_label = BodyLabel(message)
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_label)
        empty_card.setFixedHeight(100)
        self.voice_flow_layout.addWidget(empty_card)

    def _on_voice_card_clicked(self, voice_id: str) -> None:
        """音色卡片点击事件

        Args:
            voice_id: 音色 ID
        """
        # 取消之前选中的卡片
        if self._current_voice_id and self._current_voice_id in self._voice_cards:
            self._voice_cards[self._current_voice_id].set_selected(False)

        # 选中新卡片
        self._current_voice_id = voice_id
        if voice_id in self._voice_cards:
            self._voice_cards[voice_id].set_selected(True)
            logger.debug(f"选中音色: {voice_id}")

    def _on_model_changed(self, model: str) -> None:
        """模型变化事件

        Args:
            model: 模型名称
        """
        self._temp_model = model
        logger.debug(f"模型切换: {model}")

    def _on_speed_changed(self, speed: float) -> None:
        """语速变化事件

        Args:
            speed: 语速值
        """
        self._temp_speed = speed

    def _on_vol_changed(self, vol: float) -> None:
        """音量变化事件

        Args:
            vol: 音量值
        """
        self._temp_vol = vol

    def _on_pitch_changed(self, pitch: int) -> None:
        """音调变化事件

        Args:
            pitch: 音调值
        """
        self._temp_pitch = pitch

    @asyncSlot()
    async def _on_play_clicked(self) -> None:
        """播放按钮点击事件"""
        # 检查是否选中音色
        if not self._current_voice_id:
            InfoBar.warning(
                title="未选择音色",
                content="请先从列表中选择一个音色",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
            return

        # 检查文本
        text = self.text_edit.toPlainText().strip()
        if not text:
            InfoBar.warning(
                title="文本为空",
                content="请输入要测试的文本",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
            return

        # 防止重复点击
        if self._is_playing:
            return

        self._is_playing = True
        self.play_button.setEnabled(False)

        try:
            # 调用 TTS 服务
            audio_bytes = await self._tts_service.text_to_speech(
                text=text,
                voice_id=self._current_voice_id,
                model=self._temp_model,
                speed=self._temp_speed,
                vol=self._temp_vol,
                pitch=self._temp_pitch,
            )

            # 播放音频
            await audio_player.play_bytes_async(audio_bytes)

            InfoBar.success(
                title="播放成功",
                content="",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1000,
                parent=self,
            )
        except Exception as e:
            logger.exception(f"播放失败: {e}")
            InfoBar.error(
                title="播放失败",
                content=str(e),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )
        finally:
            self._is_playing = False
            self.play_button.setEnabled(True)
