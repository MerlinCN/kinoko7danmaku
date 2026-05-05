"""MiniMax 音色克隆界面"""

from loguru import logger
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qasync import asyncSlot
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    ComboBox,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    PrimaryPushButton,
    ScrollArea,
    StateToolTip,
    SubtitleLabel,
    SwitchButton,
    TextEdit,
    TitleLabel,
    ToolButton,
)
from qfluentwidgets import FluentIcon as FIF

from core.const import MINIMAX_MODELS
from core.player import audio_player
from core.qconfig import cfg
from gui.components import SingleAudioUploadWidget
from models.minimax import ClonePrompt, FilePurpose, VoiceCloneRequest, VoiceItem
from tts_service.minimax import MinimaxService


class MinimaxVoiceCloneInterface(QWidget):
    """MiniMax 音色克隆界面"""

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化 MiniMax 音色克隆界面

        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        self._tts_service = MinimaxService()
        self._cloned_voices: list[VoiceItem] = []
        self._is_processing = False
        self._is_loaded = False

        self._init_ui()

    def _init_ui(self) -> None:
        """初始化 UI"""
        # 主容器
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(36, 36, 36, 36)
        main_layout.setSpacing(20)

        # 标题
        title = TitleLabel("音色克隆")
        main_layout.addWidget(title)

        # 滚动区域
        scroll_area = ScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
        )

        # 滚动内容容器
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(20)

        # === 步骤1：上传音频卡片 ===
        upload_card = CardWidget()
        upload_layout = QVBoxLayout(upload_card)
        upload_layout.setContentsMargins(20, 20, 20, 20)
        upload_layout.setSpacing(12)

        upload_title = SubtitleLabel("1. 导入您的音频")
        upload_layout.addWidget(upload_title)

        # 源音频上传组件（单文件）
        self.source_audio_upload_widget = SingleAudioUploadWidget()
        self.source_audio_upload_widget.fileUploaded.connect(
            self._on_source_file_uploaded
        )
        upload_layout.addWidget(self.source_audio_upload_widget)

        scroll_layout.addWidget(upload_card)

        # === 步骤2：示例音频上传（必填）===
        example_card = CardWidget()
        example_layout = QVBoxLayout(example_card)
        example_layout.setContentsMargins(20, 20, 20, 20)
        example_layout.setSpacing(12)

        example_title = SubtitleLabel("2. 示例音频上传（必填）")
        example_layout.addWidget(example_title)

        # 说明文本
        example_desc = CaptionLabel(
            "上传一段 <8 秒的示例音频，并填写音频中念的台词，用于克隆音色"
        )
        example_desc.setTextColor("#606060", "#d2d2d2")
        example_desc.setWordWrap(True)
        example_layout.addWidget(example_desc)

        # 示例音频上传组件（单文件，时长<8秒，无最小时长限制）
        self.example_audio_upload_widget = SingleAudioUploadWidget(
            min_duration=0.0,
            max_duration=8.0,
            max_size_mb=20.0,
            tip_text="支持 mp3/m4a/wav 格式，建议8秒以内，最大20MB",
            purpose=FilePurpose.PROMPT_AUDIO,
        )
        self.example_audio_upload_widget.fileUploaded.connect(
            self._on_example_file_uploaded
        )
        self.example_audio_upload_widget.fileRemoved.connect(
            self._on_example_file_removed
        )
        example_layout.addWidget(self.example_audio_upload_widget)

        # 示例音频描述文本框（初始隐藏）
        self.example_desc_container = QWidget()
        example_desc_layout = QVBoxLayout(self.example_desc_container)
        example_desc_layout.setContentsMargins(0, 0, 0, 0)
        example_desc_layout.setSpacing(4)

        example_desc_label = BodyLabel("台词转录（必填）")
        example_desc_layout.addWidget(example_desc_label)

        self.example_description_edit = TextEdit()
        self.example_description_edit.setPlaceholderText(
            "请输入示例音频中念的完整台词，需与音频内容一致并以标点结尾"
        )
        self.example_description_edit.setMaximumHeight(80)
        example_desc_layout.addWidget(self.example_description_edit)

        example_layout.addWidget(self.example_desc_container)
        self.example_desc_container.hide()  # 初始隐藏

        scroll_layout.addWidget(example_card)

        # === 步骤3：高级设置卡片 ===
        advanced_card = CardWidget()
        advanced_layout = QVBoxLayout(advanced_card)
        advanced_layout.setContentsMargins(20, 20, 20, 20)
        advanced_layout.setSpacing(12)

        advanced_title = SubtitleLabel("3. 高级设置")
        advanced_layout.addWidget(advanced_title)

        # 模型选择
        model_layout = QHBoxLayout()
        model_label = BodyLabel("模型")
        self.model_combo = ComboBox()
        self.model_combo.addItems(MINIMAX_MODELS)
        self.model_combo.setCurrentText(MINIMAX_MODELS[0])  # 默认选择第一个模型
        self.model_combo.setFixedWidth(200)
        model_layout.addWidget(model_label)
        model_layout.addStretch()
        model_layout.addWidget(self.model_combo)
        advanced_layout.addLayout(model_layout)

        # 去除背景噪音
        denoise_layout = QHBoxLayout()
        denoise_label = BodyLabel("去除背景噪音")
        self.denoise_switch = SwitchButton()
        denoise_layout.addWidget(denoise_label)
        denoise_layout.addStretch()
        denoise_layout.addWidget(self.denoise_switch)
        advanced_layout.addLayout(denoise_layout)

        scroll_layout.addWidget(advanced_card)

        # === 步骤4：音色信息卡片 ===
        info_card = CardWidget()
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(20, 20, 20, 20)
        info_layout.setSpacing(12)

        info_title = SubtitleLabel("4. 音色信息")
        info_layout.addWidget(info_title)

        # 音色ID
        id_layout = QVBoxLayout()
        id_layout.setSpacing(4)
        id_label = BodyLabel("音色ID（唯一标识）")
        self.voice_id_edit = LineEdit()
        self.voice_id_edit.setPlaceholderText("输入自定义音色ID，例如：my_voice_001")
        id_layout.addWidget(id_label)
        id_layout.addWidget(self.voice_id_edit)
        info_layout.addLayout(id_layout)

        # 音色名称
        name_layout = QVBoxLayout()
        name_layout.setSpacing(4)
        name_label = BodyLabel("音色名称")
        self.voice_name_edit = LineEdit()
        self.voice_name_edit.setPlaceholderText("输入音色名称，例如：我的声音")
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.voice_name_edit)
        info_layout.addLayout(name_layout)

        scroll_layout.addWidget(info_card)

        # === 步骤5：预览测试卡片 ===
        preview_card = CardWidget()
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(20, 20, 20, 20)
        preview_layout.setSpacing(12)

        preview_title = SubtitleLabel("5. 预览测试（可选）")
        preview_layout.addWidget(preview_title)

        # 测试文本
        test_text_label = BodyLabel("测试文本（最多300字符）")
        preview_layout.addWidget(test_text_label)

        self.test_text_edit = TextEdit()
        self.test_text_edit.setPlaceholderText(
            "输入测试文本，点击播放按钮预览音色效果..."
        )
        self.test_text_edit.setMaximumHeight(100)
        self.test_text_edit.textChanged.connect(self._on_test_text_changed)
        preview_layout.addWidget(self.test_text_edit)

        # 字符计数 + 播放按钮
        preview_button_layout = QHBoxLayout()
        self.char_count_label = CaptionLabel("0 / 300")
        self.char_count_label.setTextColor("#606060", "#d2d2d2")
        preview_button_layout.addWidget(self.char_count_label)
        preview_button_layout.addStretch()

        self.preview_play_button = ToolButton(FIF.PLAY)
        self.preview_play_button.setFixedSize(32, 32)
        self.preview_play_button.setToolTip("播放预览")
        self.preview_play_button.clicked.connect(self._on_preview_play_clicked)
        preview_button_layout.addWidget(self.preview_play_button)

        preview_layout.addLayout(preview_button_layout)

        scroll_layout.addWidget(preview_card)

        # === 操作按钮区 ===
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)

        # 剩余槽位提示
        self.slot_hint_label = BodyLabel("")
        action_layout.addWidget(self.slot_hint_label)

        action_layout.addStretch()

        # 生成按钮
        self.generate_button = PrimaryPushButton(FIF.ADD, "生成音色")
        self.generate_button.clicked.connect(self._on_generate_clicked)
        action_layout.addWidget(self.generate_button)

        scroll_layout.addLayout(action_layout)

        # === 音频预览区域（初始隐藏）===
        self.preview_audio_card = CardWidget()
        preview_audio_layout = QVBoxLayout(self.preview_audio_card)
        preview_audio_layout.setContentsMargins(20, 20, 20, 20)
        preview_audio_layout.setSpacing(12)

        preview_audio_title = SubtitleLabel("生成结果预览")
        preview_audio_layout.addWidget(preview_audio_title)

        # 成功提示文本
        self.success_label = BodyLabel("")
        self.success_label.setWordWrap(True)
        preview_audio_layout.addWidget(self.success_label)

        # 播放按钮容器
        audio_control_layout = QHBoxLayout()
        audio_control_layout.setSpacing(10)

        self.play_preview_button = ToolButton(FIF.PLAY)
        self.play_preview_button.setFixedSize(48, 48)
        self.play_preview_button.setToolTip("播放预览音频")
        self.play_preview_button.clicked.connect(self._on_play_preview_audio)
        audio_control_layout.addWidget(self.play_preview_button)

        self.preview_status_label = CaptionLabel("")
        self.preview_status_label.setTextColor("#606060", "#d2d2d2")
        audio_control_layout.addWidget(self.preview_status_label)

        audio_control_layout.addStretch()
        preview_audio_layout.addLayout(audio_control_layout)

        scroll_layout.addWidget(self.preview_audio_card)
        self.preview_audio_card.hide()  # 初始隐藏

        scroll_layout.addStretch()

        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

        # 在界面初始化时加载音色列表
        self._load_voice_count()

        # 存储预览音频数据
        self._preview_audio_url: str | None = None
        self._preview_audio_bytes: bytes | None = None
        self._is_playing_preview = False

    def _load_voice_count(self) -> None:
        """加载音色数量（同步方法，在初始化时调用）"""
        # 使用 QTimer 延迟执行异步任务
        QTimer.singleShot(0, self._async_load_voice_count)

    @asyncSlot()
    async def _async_load_voice_count(self) -> None:
        """异步加载音色数量"""
        # 检查 API Key
        if not cfg.minimaxApiKey.value:
            self.slot_hint_label.setText("请先在设置中配置 MiniMax API Key")
            self.generate_button.setEnabled(False)
            return

        try:
            response = await self._tts_service.get_voice_list()
            self._cloned_voices = response.voice_cloning
            self._update_slot_hint()
            self._is_loaded = True
            logger.info(f"成功加载 {len(self._cloned_voices)} 个音色")
        except ValueError as e:
            logger.error(f"加载音色列表失败: {e}")
            self.slot_hint_label.setText("API Key 无效")
            self.generate_button.setEnabled(False)
        except Exception as e:
            logger.exception(f"加载音色列表失败: {e}")
            self.slot_hint_label.setText("网络错误，无法加载音色信息")
            self.generate_button.setEnabled(False)

    def _update_slot_hint(self) -> None:
        """更新槽位提示"""
        total_slots = 10  # 假设最大槽位数
        used_slots = len(self._cloned_voices)
        remaining = total_slots - used_slots
        self.slot_hint_label.setText(f"剩余音色槽位: {remaining} / {total_slots}")

    def _on_source_file_uploaded(self, file_response, duration: float) -> None:
        """源音频文件上传成功事件

        Args:
            file_response: 文件上传响应
            duration: 本地解析的音频时长（秒）
        """
        logger.info(
            f"源音频文件上传成功: {file_response.file.filename} ({duration:.1f}秒)"
        )

    def _on_example_file_uploaded(self, file_response, duration: float) -> None:
        """示例音频文件上传成功事件

        Args:
            file_response: 文件上传响应
            duration: 本地解析的音频时长（秒）
        """
        logger.info(f"示例音频文件上传成功: {file_response.file.filename}")
        # 示例音频时长验证（<8秒）
        if duration > 8.0:
            InfoBar.warning(
                title="示例音频过长",
                content=f"示例音频时长为 {duration:.1f}秒，建议使用8秒以内的音频以获得更好效果",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self,
            )

        # 显示描述文本框
        self.example_desc_container.show()

    def _on_example_file_removed(self) -> None:
        """示例音频文件删除事件"""
        # 隐藏描述文本框并清空内容
        self.example_desc_container.hide()
        self.example_description_edit.clear()
        logger.info("示例音频文件已删除")

    def _on_test_text_changed(self) -> None:
        """测试文本变化事件"""
        text = self.test_text_edit.toPlainText()
        char_count = len(text)

        # 限制字符数
        if char_count > 300:
            self.test_text_edit.setPlainText(text[:300])
            char_count = 300

        self.char_count_label.setText(f"{char_count} / 300")

    @asyncSlot()
    async def _on_preview_play_clicked(self) -> None:
        """预览播放按钮点击事件"""
        # TODO: 实现预览播放功能（需要临时克隆音色）
        InfoBar.info(
            title="功能开发中",
            content="预览功能暂未实现",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self,
        )

    @asyncSlot()
    async def _on_generate_clicked(self) -> None:
        """生成按钮点击事件"""
        # 检查 API Key
        if not cfg.minimaxApiKey.value:
            InfoBar.error(
                title="错误",
                content="请先在设置中配置 MiniMax API Key",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )
            return

        # 检查是否上传了源音频文件
        source_file = self.source_audio_upload_widget.get_uploaded_file()
        if not source_file:
            InfoBar.warning(
                title="缺少源音频文件",
                content="请先上传源音频文件",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
            return

        # 检查音色ID
        voice_id = self.voice_id_edit.text().strip()
        if not voice_id:
            InfoBar.warning(
                title="缺少音色ID",
                content="请输入音色ID",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
            return

        # 检查音色名称
        voice_name = self.voice_name_edit.text().strip()
        if not voice_name:
            InfoBar.warning(
                title="缺少音色名称",
                content="请输入音色名称",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
            return

        # 防止重复处理
        if self._is_processing:
            return

        self._is_processing = True
        self.generate_button.setEnabled(False)

        # 显示处理状态
        state_tooltip = StateToolTip(
            "正在生成", "正在生成音色，请稍候...", self.window()
        )
        state_tooltip.move(state_tooltip.getSuitablePos())
        state_tooltip.show()

        try:
            # 校验示例音频与转录文本（新版 API clone_prompt 为必填）
            example_file = self.example_audio_upload_widget.get_uploaded_file()
            if not example_file:
                state_tooltip.setState(False)
                state_tooltip.setTitle("缺少示例音频")
                state_tooltip.setContent("请上传 <8 秒的示例音频")
                return
            prompt_text = self.example_description_edit.toPlainText().strip()
            if not prompt_text:
                state_tooltip.setState(False)
                state_tooltip.setTitle("缺少台词转录")
                state_tooltip.setContent("请填写示例音频对应的台词转录")
                return

            clone_prompt = ClonePrompt(
                prompt_audio=example_file.file.file_id,
                prompt_text=prompt_text,
            )

            # 获取选择的模型
            selected_model = self.model_combo.currentText()

            # 构建请求
            request = VoiceCloneRequest(
                file_id=source_file.file.file_id,
                voice_id=voice_id,
                clone_prompt=clone_prompt,
                model=selected_model,
                need_noise_reduction=self.denoise_switch.isChecked(),
            )

            # 调用 API
            response = await self._tts_service.create_voice_clone(request=request)

            state_tooltip.setState(True)
            state_tooltip.setTitle("生成成功")

            InfoBar.success(
                title="生成成功",
                content=f"音色 {voice_name} 已生成",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )

            # 刷新音色数量
            await self._async_load_voice_count()

            # 显示音频预览
            if response.demo_audio:
                self._show_audio_preview(voice_id, voice_name, response.demo_audio)
            else:
                # 没有预览音频，只重置表单
                self._reset_form()

            logger.info(f"音色克隆成功: {voice_id} ({voice_name})")

        except ValueError as e:
            logger.error(f"生成音色失败: {e}")
            state_tooltip.setState(False)
            state_tooltip.setTitle("生成失败")
            state_tooltip.setContent(str(e))

            InfoBar.error(
                title="生成失败",
                content=str(e),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )
        except Exception as e:
            logger.exception(f"生成音色失败: {e}")
            state_tooltip.setState(False)
            state_tooltip.setTitle("生成失败")
            state_tooltip.setContent("网络请求失败，请检查网络连接")

            InfoBar.error(
                title="生成失败",
                content="网络请求失败，请检查网络连接",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )
        finally:
            self._is_processing = False
            self.generate_button.setEnabled(True)

    def _reset_form(self) -> None:
        """重置表单"""
        self.voice_id_edit.clear()
        self.voice_name_edit.clear()
        self.model_combo.setCurrentIndex(0)  # 重置为第一个模型
        self.denoise_switch.setChecked(False)
        self.test_text_edit.clear()
        self.source_audio_upload_widget.clear_uploaded_file()
        self.example_audio_upload_widget.clear_uploaded_file()
        self.example_description_edit.clear()
        self.example_desc_container.hide()  # 隐藏描述文本框
        # 隐藏预览区域
        self.preview_audio_card.hide()
        self._preview_audio_url = None
        self._preview_audio_bytes = None

    def _show_audio_preview(
        self, voice_id: str, voice_name: str, audio_url: str
    ) -> None:
        """显示音频预览区域

        Args:
            voice_id: 音色ID
            voice_name: 音色名称
            audio_url: 预览音频URL
        """
        self._preview_audio_url = audio_url
        self._preview_audio_bytes = None  # 清空之前的音频数据

        # 更新提示文本
        self.success_label.setText(
            f"音色 <b>{voice_name}</b> (ID: {voice_id}) 已成功生成！\n点击播放按钮试听预览音频。"
        )
        self.preview_status_label.setText("点击播放预览音频")

        # 显示预览区域
        self.preview_audio_card.show()

        logger.info(f"显示音频预览: {audio_url}")

    @asyncSlot()
    async def _on_play_preview_audio(self) -> None:
        """播放预览音频"""
        if not self._preview_audio_url:
            InfoBar.warning(
                title="无预览音频",
                content="没有可用的预览音频",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
            return

        # 防止重复播放
        if self._is_playing_preview:
            return

        self._is_playing_preview = True
        self.play_preview_button.setEnabled(False)
        self.preview_status_label.setText("正在播放...")

        try:
            # 如果还没有下载音频数据，先下载
            if not self._preview_audio_bytes:
                self.preview_status_label.setText("正在下载音频...")
                logger.info(f"下载预览音频: {self._preview_audio_url}")

                # 使用 httpx 下载音频
                import httpx

                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(self._preview_audio_url)
                    response.raise_for_status()
                    self._preview_audio_bytes = response.content

                logger.info(f"音频下载完成: {len(self._preview_audio_bytes)} 字节")

            # 播放音频
            self.preview_status_label.setText("正在播放...")
            await audio_player.play_bytes_async(self._preview_audio_bytes)

            self.preview_status_label.setText("播放完成，可以重新播放")

            InfoBar.success(
                title="播放完成",
                content="",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1000,
                parent=self,
            )

        except Exception as e:
            logger.exception(f"播放预览音频失败: {e}")
            self.preview_status_label.setText("播放失败，请重试")

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
            self._is_playing_preview = False
            self.play_preview_button.setEnabled(True)
