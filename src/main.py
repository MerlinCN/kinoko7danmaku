from pathlib import Path
import tempfile

import gradio as gr
import gradio.themes as themes
import sounddevice as sd
from loguru import logger

from audio_player import StreamPlayer
from config import config_manager, TTSConfig

# 全局 StreamPlayer 实例
stream_player = StreamPlayer()

# 存储临时文件列表用于清理 (使用 pathlib.Path)
temp_files: list[Path] = []


def cleanup_temp_file(file_path: Path):
    """清理临时文件"""
    try:
        if file_path and file_path.exists():
            file_path.unlink()
            if file_path in temp_files:
                temp_files.remove(file_path)
    except Exception as e:
        logger.warning(f"清理临时文件失败: {e}")


def cleanup_all_temp_files():
    """清理所有临时文件"""
    for file_path in temp_files.copy():
        cleanup_temp_file(file_path)


def update_all_config(*args) -> tuple:
    """更新所有配置并返回更新后的值"""
    # 定义字段名称，与界面输入组件顺序一致
    field_names = [
        "room_id",
        "gift_threshold",
        "api_url",
        "normal_danmaku_on",
        "guard_on",
        "super_chat_on",
        "debug",
    ]

    # 将位置参数转换为字典
    config_dict = dict(zip(field_names, args))

    try:
        # 使用字典创建配置对象，利用pydantic的验证
        config = TTSConfig(**config_dict)

        # 验证必需字段
        if not config.api_url.strip():
            gr.Error("API URL 不能为空")
            return args

        if config.room_id <= 0:
            gr.Error("房间号必须大于0")
            return args

        # 更新配置
        success = config_manager.update_config(config)

        if success:
            gr.Info("配置已成功保存")
            # 使用model_dump()获取所有字段值，按顺序返回
            config_values = config.model_dump()
            return tuple(config_values[field] for field in field_names)
        else:
            gr.Error("保存配置失败")
            return args

    except Exception as e:
        gr.Error(f"更新失败: {str(e)}")
        return args


async def play_audio_with_params(
    text: str,
    device_choice: int,  # 改为接收整数索引
    chunk_length: int,
    seed: int,
    use_memory_cache: str,
    normalize: bool,
    streaming: bool,
    max_new_tokens: int,
    top_p: float,
    repetition_penalty: float,
    temperature: float,
):
    """使用指定参数播放音频"""
    if not text.strip():
        return "❌ 请输入要播放的文本", None

    try:
        # 设置播放设备
        stream_player.set_output_device(device_choice)

        # 使用指定参数播放并获取音频数据
        audio_data = await stream_player.play_from_text(
            text=text,
            chunk_length=chunk_length,
            seed=seed,
            use_memory_cache=use_memory_cache,
            normalize=normalize,
            streaming=streaming,
            max_new_tokens=max_new_tokens,
            top_p=top_p,
            repetition_penalty=repetition_penalty,
            temperature=temperature,
        )

        status_msg = f"✅ 成功播放音频: {text[:50]}{'...' if len(text) > 50 else ''}"

        # 将音频数据保存为临时文件
        if audio_data:
            # 使用pathlib创建临时文件
            temp_dir = Path(tempfile.gettempdir())
            # 创建带有唯一名称的临时文件路径
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".wav", dir=temp_dir
            ) as temp_file:
                temp_file_path = Path(temp_file.name)

            # 写入音频数据
            temp_file_path.write_bytes(audio_data)

            # 添加到临时文件列表
            temp_files.append(temp_file_path)

            return status_msg, str(temp_file_path)  # Gradio需要字符串路径
        else:
            return status_msg, None

    except Exception as e:
        error_msg = f"❌ 播放失败: {str(e)}"
        logger.error(error_msg)
        return error_msg, None


def create_config_interface():
    """创建配置界面"""
    with gr.Blocks() as config_tab:
        current_config = config_manager.config

        with gr.Row():
            # 左侧：主要配置
            with gr.Column(scale=2):
                gr.Markdown("#### 🏠 直播间配置")
                with gr.Group():
                    room_id_input = gr.Number(
                        label="房间号",
                        value=current_config.room_id,
                        precision=0,
                        info="直播间房间号",
                    )

                    gift_threshold_input = gr.Number(
                        label="礼物阈值（元）",
                        value=current_config.gift_threshold,
                        precision=0,
                        info="≥这个值（单位：元）才会触发礼物",
                    )

                gr.Markdown("#### 🌐 API 配置")
                with gr.Group():
                    api_url_input = gr.Textbox(
                        label="API 地址",
                        value=current_config.api_url,
                        placeholder="http://localhost:8080/v1/tts",
                        info="TTS API 服务地址",
                    )

            # 右侧：开关和高级配置
            with gr.Column(scale=1):
                gr.Markdown("#### 🔘 触发开关")
                with gr.Group():
                    normal_danmaku_on_input = gr.Checkbox(
                        label="普通弹幕触发",
                        value=current_config.normal_danmaku_on,
                        info="普通弹幕是否触发",
                    )

                    guard_on_input = gr.Checkbox(
                        label="舰长触发",
                        value=current_config.guard_on,
                        info="舰长是否触发",
                    )

                    super_chat_on_input = gr.Checkbox(
                        label="醒目留言触发",
                        value=current_config.super_chat_on,
                        info="醒目留言是否触发",
                    )

                gr.Markdown("#### 🐛 调试配置")
                with gr.Group():
                    debug_input = gr.Checkbox(
                        label="调试模式",
                        value=current_config.debug,
                        info="是否开启调试模式，不开启就行了",
                    )

        # 操作按钮
        with gr.Row():
            save_btn = gr.Button("💾 保存所有配置", variant="primary", scale=2)

        gr.Markdown("#### 💡 使用说明")
        gr.Markdown("""
        - **房间号**: 要监听的直播间房间号
        - **礼物阈值**: 只有价值达到这个金额的礼物才会触发语音
        - **API配置**: TTS服务的地址
        - **触发开关**: 控制哪些类型的消息会触发语音
        - **别名配置**: 替换特定词语，每行设置一个原词和替换词
        - 修改配置后点击保存即可生效，无需重启程序
        """)

        # 基础配置输入组件列表
        basic_config_inputs = [
            room_id_input,
            gift_threshold_input,
            api_url_input,
            normal_danmaku_on_input,
            guard_on_input,
            super_chat_on_input,
            debug_input,
        ]

        # 绑定保存事件
        save_btn.click(
            fn=update_all_config,
            inputs=basic_config_inputs,
            outputs=basic_config_inputs,
        )

    return config_tab


def create_tts_interface():
    """创建TTS界面"""
    with gr.Blocks() as tts_tab:
        with gr.Row():
            # 左侧：文本输入和设备选择
            with gr.Column(scale=2):
                gr.Markdown("#### 📝 文本输入")
                text_input = gr.Textbox(
                    label="输入文本",
                    placeholder="请输入要转换为语音的文本...",
                    lines=5,
                    max_lines=10,
                )

                gr.Markdown("#### 🔊 播放设备")
                device_dropdown = gr.Dropdown(
                    label="选择播放设备",
                    choices=stream_player.get_output_devices(),
                    value=sd.default.device[1],  # 默认设备的索引值
                    type="value",  # 输出实际设备索引值
                    interactive=True,
                )

                # 播放按钮和状态
                with gr.Row():
                    play_button = gr.Button(
                        "🎵 播放音频", variant="primary", size="lg", scale=2
                    )
                    refresh_devices_btn = gr.Button("🔄 刷新设备", size="lg", scale=1)

            # 右侧：参数控制
            with gr.Column(scale=1):
                gr.Markdown("#### ⚙️ TTS 参数调节")

                with gr.Group():
                    gr.Markdown("**基础参数**")
                    chunk_length = gr.Slider(
                        label="分块长度 (chunk_length)",
                        minimum=50,
                        maximum=500,
                        value=200,
                        step=10,
                        info="文本分块处理长度",
                    )

                    seed = gr.Number(
                        label="随机种子 (seed)",
                        value=-1,
                        precision=0,
                        info="设置为-1使用随机种子",
                    )

                    use_memory_cache = gr.Radio(
                        label="内存缓存 (use_memory_cache)",
                        choices=["on", "off"],
                        value="off",
                        info="是否使用内存缓存",
                    )

                with gr.Group():
                    gr.Markdown("**音频处理**")
                    normalize = gr.Checkbox(
                        label="音频标准化 (normalize)",
                        value=True,
                        info="标准化音频音量",
                    )

                    streaming = gr.Checkbox(
                        label="流式传输 (streaming)",
                        value=False,
                        info="启用流式音频传输",
                    )

                with gr.Group():
                    gr.Markdown("**生成参数**")
                    max_new_tokens = gr.Slider(
                        label="最大新标记数 (max_new_tokens)",
                        minimum=256,
                        maximum=2048,
                        value=1024,
                        step=64,
                        info="最大生成的标记数量",
                    )

                    top_p = gr.Slider(
                        label="Top-p (nucleus sampling)",
                        minimum=0.1,
                        maximum=1.0,
                        value=0.8,
                        step=0.05,
                        info="核采样概率阈值",
                    )

                    repetition_penalty = gr.Slider(
                        label="重复惩罚 (repetition_penalty)",
                        minimum=1.0,
                        maximum=2.0,
                        value=1.1,
                        step=0.05,
                        info="避免重复的惩罚强度",
                    )

                    temperature = gr.Slider(
                        label="温度 (temperature)",
                        minimum=0.1,
                        maximum=2.0,
                        value=0.8,
                        step=0.1,
                        info="控制生成的随机性",
                    )

        # 输出状态和音频播放器
        with gr.Row():
            with gr.Column(scale=1):
                output = gr.Textbox(label="📊 播放状态", interactive=False, lines=3)
            with gr.Column(scale=1):
                audio_output = gr.Audio(
                    label="🎵 生成的音频",
                    type="filepath",
                    interactive=False,
                    show_download_button=True,
                    show_share_button=False,
                )

        # 预设参数快捷按钮
        with gr.Row():
            gr.Markdown("#### 🎯 预设参数")

        with gr.Row():
            preset_high_quality = gr.Button("🏆 高质量", size="sm")
            preset_fast = gr.Button("⚡ 快速", size="sm")
            preset_creative = gr.Button("🎨 创意", size="sm")
            preset_stable = gr.Button("🛡️ 稳定", size="sm")

        # 事件绑定
        def refresh_devices():
            return gr.Dropdown(
                choices=stream_player.get_output_devices(), value=sd.default.device[1]
            )

        def set_high_quality_preset():
            return [300, -1, "on", True, False, 1024, 0.9, 1.0, 0.7]

        def set_fast_preset():
            return [150, -1, "off", True, True, 512, 0.8, 1.2, 1.0]

        def set_creative_preset():
            return [200, -1, "off", True, False, 1024, 0.95, 1.05, 0.9]

        def set_stable_preset():
            return [200, -1, "on", True, False, 1024, 0.8, 1.1, 0.8]

        # 绑定主要播放事件
        play_inputs = [
            text_input,
            device_dropdown,
            chunk_length,
            seed,
            use_memory_cache,
            normalize,
            streaming,
            max_new_tokens,
            top_p,
            repetition_penalty,
            temperature,
        ]

        play_button.click(
            fn=play_audio_with_params,
            inputs=play_inputs,
            outputs=[output, audio_output],
        )

        text_input.submit(
            fn=play_audio_with_params,
            inputs=play_inputs,
            outputs=[output, audio_output],
        )

        # 刷新设备
        refresh_devices_btn.click(fn=refresh_devices, outputs=device_dropdown)

        # 预设参数
        preset_outputs = [
            chunk_length,
            seed,
            use_memory_cache,
            normalize,
            streaming,
            max_new_tokens,
            top_p,
            repetition_penalty,
            temperature,
        ]

        preset_high_quality.click(fn=set_high_quality_preset, outputs=preset_outputs)
        preset_fast.click(fn=set_fast_preset, outputs=preset_outputs)
        preset_creative.click(fn=set_creative_preset, outputs=preset_outputs)
        preset_stable.click(fn=set_stable_preset, outputs=preset_outputs)

    return tts_tab


def create_gradio_interface():
    """创建带有多页签的界面"""
    # 创建各个页签
    tts_tab = create_tts_interface()
    config_tab = create_config_interface()

    # 使用 TabbedInterface 组合页签
    demo = gr.TabbedInterface(
        [tts_tab, config_tab],
        ["🎵 语音合成", "⚙️ 系统配置"],
        title="AI 小肉包",
        theme=themes.Soft(),
        css="""
        .gradio-container {
            max-width: 1200px !important;
            margin: 0 auto !important;
        }
        .parameter-group {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
        }
        """,
    )

    return demo


def main():
    """主函数"""
    try:
        # 初始化时打印设备信息
        logger.info("初始化音频设备...")
        logger.info(f"当前 API URL: {config_manager.get_api_url()}")
        # stream_player.print_devices()

        # 创建并启动 Gradio 界面
        demo = create_gradio_interface()
        demo.launch(
            server_name="127.0.0.1",
            server_port=7860,  # 使用默认端口
            share=False,
            show_error=True,
            inbrowser=True,
        )
    finally:
        # 清理资源
        stream_player.close()
        cleanup_all_temp_files()  # 清理所有临时文件


if __name__ == "__main__":
    main()
