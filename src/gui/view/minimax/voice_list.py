"""MiniMax 音色列表界面"""

from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QMouseEvent, QPaintEvent, QPainter, QPen, QShowEvent
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from loguru import logger
from qasync import asyncSlot
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    ComboBoxSettingCard,
    FlowLayout,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    OptionsConfigItem,
    OptionsValidator,
    PushButton,
    RangeConfigItem,
    RangeValidator,
    ScrollArea,
    StateToolTip,
    SubtitleLabel,
    TextEdit,
    ToolButton,
)
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets.common.font import getFont
from qfluentwidgets.common.style_sheet import setCustomStyleSheet

from core.const import MINIMAX_MODELS
from core.player import audio_player
from core.qconfig import cfg
from gui.components import FloatRangeSettingCard
from gui.components.minimax_kit import ACCENT, HeroCard, accent_button_qss
from tts_service.minimax import MinimaxService

if TYPE_CHECKING:
    from models.minimax import VoiceItem


class VoiceCard(CardWidget):
    """音色卡片

    展示音色名称与 ID，点击选中，选中后以强调色描边标记。
    """

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

        self.setFixedHeight(76)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(self.voice_id)

        self._init_ui()

    def _init_ui(self) -> None:
        """初始化 UI"""
        self.hBoxLayout = QHBoxLayout(self)
        self.vBoxLayout = QVBoxLayout()

        # 音色名称
        self.titleLabel = BodyLabel('', self)
        self.titleLabel.setFont(getFont(15, QFont.Weight.DemiBold))
        self.titleLabel.setText(self._elide(self.voice_name))

        # 音色 ID（小字）
        self.idLabel = CaptionLabel('', self)
        self.idLabel.setTextColor('#606060', '#d2d2d2')
        self.idLabel.setText(self._elide(self.voice_id))

        # 复制按钮
        self.copyButton = ToolButton(FIF.COPY, self)
        self.copyButton.setFixedSize(32, 32)
        self.copyButton.setToolTip('复制音色 ID')
        self.copyButton.clicked.connect(self._on_copy_clicked)

        # 布局
        self.hBoxLayout.setContentsMargins(18, 10, 10, 10)
        self.hBoxLayout.setSpacing(12)

        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(2)
        self.vBoxLayout.addWidget(self.titleLabel, 0, Qt.AlignmentFlag.AlignVCenter)
        self.vBoxLayout.addWidget(self.idLabel, 0, Qt.AlignmentFlag.AlignVCenter)
        self.vBoxLayout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.hBoxLayout.addLayout(self.vBoxLayout, 1)
        self.hBoxLayout.addWidget(self.copyButton, 0, Qt.AlignmentFlag.AlignRight)

    def _elide(self, text: str) -> str:
        """按卡片可用宽度省略过长的文本

        Args:
            text: 原始文本

        Returns:
            str: 省略后的文本
        """
        metrics = self.titleLabel.fontMetrics()
        return metrics.elidedText(text, Qt.TextElideMode.ElideRight, 188)

    def _on_copy_clicked(self) -> None:
        """复制按钮点击事件"""
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.voice_id)

        InfoBar.success(
            title='复制成功',
            content=f'已复制音色 ID: {self.voice_id}',
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self.window(),
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
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
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """绘制选中态的强调色描边与底色

        Args:
            event: 绘制事件
        """
        super().paintEvent(event)
        if not self._is_selected:
            return

        painter = QPainter(self)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing)

        tint = QColor(ACCENT)
        tint.setAlpha(20)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(tint)
        painter.drawRoundedRect(self.rect(), 6, 6)

        pen = QPen(QColor(ACCENT))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 6, 6)
        painter.end()


class MinimaxVoiceListInterface(QWidget):
    """MiniMax 音色列表界面

    左侧浏览与搜索音色，右侧试听并调整合成参数。
    """

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

        # 临时配置项（仅用于 UI 组件，不保存到配置文件）
        self._temp_model_config = OptionsConfigItem(
            group='VoiceListTemp',
            name='TempModel',
            default=MINIMAX_MODELS[0],
            validator=OptionsValidator(MINIMAX_MODELS),
        )
        self._temp_speed_config = RangeConfigItem(
            group='VoiceListTemp',
            name='TempSpeed',
            default=1.0,
            validator=RangeValidator(0.5, 2.0),
        )
        self._temp_vol_config = RangeConfigItem(
            group='VoiceListTemp',
            name='TempVol',
            default=1.0,
            validator=RangeValidator(0.0, 2.0),
        )
        self._temp_pitch_config = RangeConfigItem(
            group='VoiceListTemp',
            name='TempPitch',
            default=0,
            validator=RangeValidator(-12, 12),
        )

        self._is_playing = False
        self._is_loaded = False  # 是否已加载过音色列表

        self._init_ui()

    def _init_ui(self) -> None:
        """初始化界面布局"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(36, 36, 36, 36)
        main_layout.setSpacing(20)

        self.hero = HeroCard(
            '音色库',
            '音色列表',
            '点击选中任意音色，试听满意后再应用为播报音色。',
            self,
        )
        main_layout.addWidget(self.hero)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        content_layout.addWidget(self._build_voice_panel(), 3)
        content_layout.addLayout(self._build_side_panel(), 2)

        main_layout.addLayout(content_layout, 1)

    def _build_voice_panel(self) -> QWidget:
        """构建左侧音色面板

        Returns:
            左侧面板组件
        """
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        header_layout.addWidget(SubtitleLabel('可用音色'))
        self.count_label = CaptionLabel('', panel)
        self.count_label.setTextColor(ACCENT, ACCENT)
        header_layout.addWidget(self.count_label, 0, Qt.AlignmentFlag.AlignVCenter)
        header_layout.addStretch()

        self.search_edit = LineEdit(panel)
        self.search_edit.setPlaceholderText('搜索音色名称或 ID')
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setFixedWidth(220)
        self.search_edit.textChanged.connect(self._on_search_changed)
        header_layout.addWidget(self.search_edit)

        self.refresh_btn = ToolButton(FIF.SYNC, panel)
        self.refresh_btn.setToolTip('重新加载音色列表')
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        header_layout.addWidget(self.refresh_btn)
        layout.addLayout(header_layout)

        self.scroll_area = ScrollArea(panel)
        self.scroll_area.setWidgetResizable(True)

        self.voice_container = QWidget()
        self.voice_flow_layout = FlowLayout(self.voice_container, needAni=True, isTight=True)
        self.voice_flow_layout.setContentsMargins(0, 0, 0, 0)
        self.voice_flow_layout.setHorizontalSpacing(10)
        self.voice_flow_layout.setVerticalSpacing(10)

        self.scroll_area.setWidget(self.voice_container)
        layout.addWidget(self.scroll_area)
        return panel

    def _build_side_panel(self) -> QVBoxLayout:
        """构建右侧试听与参数面板

        Returns:
            右侧布局
        """
        side_layout = QVBoxLayout()
        side_layout.setSpacing(16)

        # 试听卡片
        self.test_card = CardWidget(self)
        test_layout = QVBoxLayout(self.test_card)
        test_layout.setContentsMargins(20, 16, 20, 16)
        test_layout.setSpacing(12)

        test_header = QHBoxLayout()
        test_header.addWidget(SubtitleLabel('音色试听', self.test_card))
        test_header.addStretch()
        self.selected_label = CaptionLabel('未选择音色', self.test_card)
        test_header.addWidget(self.selected_label, 0, Qt.AlignmentFlag.AlignVCenter)
        test_layout.addLayout(test_header)

        self.text_edit = TextEdit(self.test_card)
        self.text_edit.setPlaceholderText('输入测试文本，听听这个音色的效果…')
        self.text_edit.setFixedHeight(120)
        test_layout.addWidget(self.text_edit)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.play_button = PushButton('试听', self.test_card)
        self.play_button.setIcon(FIF.PLAY)
        setCustomStyleSheet(self.play_button, accent_button_qss(), accent_button_qss())
        self.play_button.clicked.connect(self._on_play_clicked)
        button_layout.addWidget(self.play_button)
        test_layout.addLayout(button_layout)

        side_layout.addWidget(self.test_card)

        # 参数卡片
        self.param_card = CardWidget(self)
        param_layout = QVBoxLayout(self.param_card)
        param_layout.setContentsMargins(20, 16, 20, 16)
        param_layout.setSpacing(8)
        param_layout.addWidget(SubtitleLabel('音色参数', self.param_card))

        self.model_card = ComboBoxSettingCard(
            configItem=self._temp_model_config,
            icon=FIF.ROBOT,
            title='模型',
            content='设置 TTS 模型',
            texts=MINIMAX_MODELS,
            parent=self.param_card,
        )
        self.model_card.comboBox.currentTextChanged.connect(self._on_model_changed)
        param_layout.addWidget(self.model_card)

        self.speed_card = FloatRangeSettingCard(
            configItem=self._temp_speed_config,
            icon=FIF.SPEED_OFF,
            title='语速',
            content='调整语音播放速度（0.5-2.0）',
            step=0.1,
            decimals=1,
            parent=self.param_card,
        )
        self.speed_card.valueChanged.connect(self._on_speed_changed)
        param_layout.addWidget(self.speed_card)

        self.vol_card = FloatRangeSettingCard(
            configItem=self._temp_vol_config,
            icon=FIF.VOLUME,
            title='音量',
            content='调整语音音量（0.0-2.0）',
            step=0.1,
            decimals=1,
            parent=self.param_card,
        )
        self.vol_card.valueChanged.connect(self._on_vol_changed)
        param_layout.addWidget(self.vol_card)

        self.pitch_card = FloatRangeSettingCard(
            configItem=self._temp_pitch_config,
            icon=FIF.MUSIC,
            title='音调',
            content='调整语音音调（-12-12）',
            step=1,
            decimals=0,
            parent=self.param_card,
        )
        self.pitch_card.valueChanged.connect(self._on_pitch_changed)
        param_layout.addWidget(self.pitch_card)

        side_layout.addWidget(self.param_card)
        side_layout.addStretch(1)
        return side_layout

    def showEvent(self, event: QShowEvent) -> None:
        """界面显示事件

        Args:
            event: 显示事件
        """
        super().showEvent(event)
        if not self._is_loaded:
            QTimer.singleShot(0, self._load_voice_list)

    async def load_voice_list(self) -> None:
        """异步加载音色列表"""
        self._is_loaded = False
        await self._fetch_voice_list()

    @asyncSlot()
    async def _load_voice_list(self) -> None:
        """首次显示时异步加载音色列表"""
        await self._fetch_voice_list()

    async def _fetch_voice_list(self) -> None:
        """请求并渲染音色列表"""
        if not cfg.minimaxApiKey.value:
            self._show_empty_state('请先在设置中配置 MiniMax API Key')
            return

        state_tooltip = StateToolTip('正在加载', '加载音色列表中...', self.window())
        state_tooltip.move(state_tooltip.getSuitablePos())
        state_tooltip.show()

        try:
            response = await self._tts_service.get_voice_list()
            self._voices = response.voice_cloning
            self._update_voice_list()
            state_tooltip.setState(True)
            state_tooltip.setTitle('加载成功')
            self._is_loaded = True
            logger.info(f'成功加载 {len(self._voices)} 个音色')
        except ValueError as e:
            logger.error(f'加载音色列表失败: {e}')
            state_tooltip.setState(False)
            state_tooltip.setTitle('加载失败')
            state_tooltip.setContent(str(e))
            self._show_empty_state(f'加载失败: {e}')
        except Exception as e:
            logger.exception(f'加载音色列表失败: {e}')
            state_tooltip.setState(False)
            state_tooltip.setTitle('加载失败')
            state_tooltip.setContent('网络请求失败，请检查网络连接')
            self._show_empty_state('加载失败，请检查网络连接和 API Key 是否正确')

    def _update_voice_list(self) -> None:
        """更新音色列表显示"""
        for card in self._voice_cards.values():
            self.voice_flow_layout.removeWidget(card)
            card.deleteLater()
        self._voice_cards.clear()

        for voice in self._voices:
            card = VoiceCard(voice.voice_id, voice.voice_name, self.voice_container)
            card.setFixedWidth(260)
            card.voiceSelected.connect(self._on_voice_card_clicked)
            self._voice_cards[voice.voice_id] = card
            self.voice_flow_layout.addWidget(card)

        self.count_label.setText(f'{len(self._voices)} 个')
        self._apply_filter()
        self._restore_selection()

    def _restore_selection(self) -> None:
        """恢复上一次选中的音色卡片状态"""
        if self._current_voice_id in self._voice_cards:
            self._voice_cards[self._current_voice_id].set_selected(True)

    def _apply_filter(self) -> None:
        """按搜索关键字过滤音色卡片"""
        keyword = self.search_edit.text().strip().lower()
        for voice_id, card in self._voice_cards.items():
            matched = not keyword or keyword in card.voice_name.lower() or keyword in voice_id.lower()
            card.setVisible(matched)

    def _on_search_changed(self, _text: str) -> None:
        """搜索框内容变化

        Args:
            _text: 搜索文本
        """
        self._apply_filter()

    def _on_refresh_clicked(self, _checked: bool = False) -> None:
        """刷新音色列表"""
        self._load_voice_list()

    def _show_empty_state(self, message: str) -> None:
        """显示空状态提示

        Args:
            message: 提示信息
        """
        for card in self._voice_cards.values():
            self.voice_flow_layout.removeWidget(card)
            card.deleteLater()
        self._voice_cards.clear()
        self.count_label.setText('')

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
        if self._current_voice_id and self._current_voice_id in self._voice_cards:
            self._voice_cards[self._current_voice_id].set_selected(False)

        self._current_voice_id = voice_id
        if voice_id in self._voice_cards:
            card = self._voice_cards[voice_id]
            card.set_selected(True)
            text = f'当前音色 · {card.voice_name}'
            elided = self.selected_label.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight, 260)
            self.selected_label.setText(elided)
            self.selected_label.setToolTip(f'{card.voice_name}（{voice_id}）')
            logger.debug(f'选中音色: {voice_id}')

    def _on_model_changed(self, model: str) -> None:
        """模型变化事件

        Args:
            model: 模型名称
        """
        self._temp_model = model
        logger.debug(f'模型切换: {model}')

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

    def _on_pitch_changed(self, pitch: float) -> None:
        """音调变化事件

        Args:
            pitch: 音调值（浮点数，需转换为整数）
        """
        self._temp_pitch = int(pitch)

    @asyncSlot()
    async def _on_play_clicked(self) -> None:
        """播放按钮点击事件"""
        if not self._current_voice_id:
            InfoBar.warning(
                title='未选择音色',
                content='请先从列表中选择一个音色',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
            return

        text = self.text_edit.toPlainText().strip()
        if not text:
            InfoBar.warning(
                title='文本为空',
                content='请输入要测试的文本',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
            return

        if self._is_playing:
            return

        self._is_playing = True
        self.play_button.setEnabled(False)
        self.play_button.setText('合成中…')

        try:
            audio_bytes = await self._tts_service.text_to_speech(
                text=text,
                voice_id=self._current_voice_id,
                model=self._temp_model,
                speed=self._temp_speed,
                vol=self._temp_vol,
                pitch=self._temp_pitch,
            )
            await audio_player.play_bytes_async(audio_bytes)
        except Exception as e:
            logger.exception(f'播放失败: {e}')
            InfoBar.error(
                title='播放失败',
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
            self.play_button.setText('试听')
