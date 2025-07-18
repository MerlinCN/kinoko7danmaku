import json
from typing import get_origin

import gradio as gr
import gradio.themes as themes
import sounddevice as sd

from audio_player import get_stream_player, play_audio_with_params
from config import TTSConfig, config_manager
from pydantic_gradio_builder import PydanticGradioBuilder


def create_config_interface():
    """创建配置界面"""
    # 使用新的构建器
    builder = PydanticGradioBuilder(TTSConfig)
    current_config = config_manager.config

    with gr.Blocks() as config_tab:
        # 创建字段到组件的映射
        field_components = {}

        # 左右两列布局，按顺序一左一右分配
        with gr.Row():
            # 左列
            with gr.Column(scale=1):
                for i, field_name in enumerate(builder.field_names):
                    if i % 2 == 0:  # 偶数索引放左列
                        current_value = getattr(current_config, field_name)
                        component = builder.create_component(field_name, current_value)
                        field_components[field_name] = component

            # 右列
            with gr.Column(scale=1):
                for i, field_name in enumerate(builder.field_names):
                    if i % 2 == 1:  # 奇数索引放右列
                        current_value = getattr(current_config, field_name)
                        component = builder.create_component(field_name, current_value)
                        field_components[field_name] = component

        # 按照pydantic模型字段顺序排列组件（保持原有的输入顺序）
        config_inputs = [
            field_components[field_name]
            for field_name in builder.field_names
            if field_name in field_components
        ]

        # 操作按钮
        with gr.Row():
            save_btn = gr.Button("💾 保存所有配置", variant="primary", scale=2)

        # 创建更新函数并绑定事件
        update_function = builder.create_update_function(config_manager)

        # 创建刷新函数
        def refresh_config():
            """从文件中刷新配置"""
            # 重新从文件加载配置
            config_manager.load_config()
            current_config = config_manager.config

            # 为所有字段返回最新值
            return_values = []
            for field_name in builder.field_names:
                value = getattr(current_config, field_name)
                if get_origin(builder.field_info[field_name].annotation) is dict:
                    return_values.append(
                        json.dumps(value, ensure_ascii=False, indent=4)
                    )
                else:
                    return_values.append(value)

            return tuple(return_values)

        # 绑定保存按钮
        save_btn.click(
            fn=update_function,
            inputs=config_inputs,
            outputs=config_inputs,
        )

        # 界面加载时自动刷新配置
        config_tab.load(
            fn=refresh_config,
            inputs=[],
            outputs=config_inputs,
        )

    return config_tab


def create_tts_interface():
    """创建TTS界面"""
    stream_player = get_stream_player()

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
            return gr.update(
                choices=stream_player.get_output_devices(), value=sd.default.device[1]
            )

        def on_device_change(device_choice):
            """设备选择变更时的处理函数"""
            try:
                result = stream_player.set_output_device(device_choice)
                device_info: dict = sd.query_devices(device_choice)
                if result:
                    gr.Info(f"✅ 已切换到设备: {device_info['name']}")
                else:
                    gr.Warning(f"⚠️ 设备切换失败: {device_choice}")
            except Exception as e:
                gr.Error(f"❌ 设备切换错误: {str(e)}")
            return device_choice

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
            outputs=[audio_output],
        )

        # 设备选择变更事件
        device_dropdown.change(
            fn=on_device_change, inputs=[device_dropdown], outputs=[device_dropdown]
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
        [config_tab, tts_tab],
        ["⚙️ 系统配置", "🎵 语音合成"],
        title="AI弹幕姬",
        theme=themes.Soft(),
    )

    return demo
