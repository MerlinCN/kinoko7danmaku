"""MiniMax 音色列表界面"""

from loguru import logger
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qasync import asyncSlot
from qfluentwidgets import (
    CardWidget,
    ComboBox,
    InfoBar,
    InfoBarPosition,
    Slider,
    StateToolTip,
    SubtitleLabel,
    TextEdit,
    TitleLabel,
    ToolButton,
)
from qfluentwidgets import (
    FluentIcon as FIF,
)

from core.const import MINIMAX_MODELS
from core.player import audio_player
from core.qconfig import cfg
from models.minimax import VoiceItem
from tts_service.minimax import MinimaxService


class MinimaxVoiceListInterface(QWidget):
    """MiniMax 音色列表界面"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._voices: list[VoiceItem] = []
        self._tts_service = MinimaxService()
        self._current_voice_id: str | None = None

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

        # === 左侧面板 (280px 固定宽度) ===
        left_panel = QWidget()
        left_panel.setFixedWidth(280)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        # 左侧标题
        left_title = SubtitleLabel("可用音色")
        left_layout.addWidget(left_title)

        # 音色列表
        self.voice_list = QListWidget()
        self.voice_list.currentItemChanged.connect(self._on_voice_selected)
        left_layout.addWidget(self.voice_list)

        content_layout.addWidget(left_panel)

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

        content_layout.addLayout(right_layout, 1)  # 右侧自适应宽度

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
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

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
        self.voice_list.clear()
        for voice in self._voices:
            display_name = voice.voice_name or voice.voice_id
            item = QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, voice.voice_id)
            self.voice_list.addItem(item)

    def _show_empty_state(self, message: str) -> None:
        """显示空状态提示

        Args:
            message: 提示信息
        """
        self.voice_list.clear()
        item = QListWidgetItem(message)
        item.setFlags(Qt.ItemFlag.NoItemFlags)  # 禁用选择
        self.voice_list.addItem(item)

    def _on_voice_selected(
        self, current: QListWidgetItem | None, previous: QListWidgetItem | None
    ) -> None:
        """音色选中事件

        Args:
            current: 当前选中项
            previous: 之前选中项
        """
        if current:
            voice_id = current.data(Qt.ItemDataRole.UserRole)
            if voice_id:
                self._current_voice_id = voice_id
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
