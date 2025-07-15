import json
import tempfile
from pathlib import Path
from typing import get_origin

import gradio as gr
import gradio.themes as themes
import sounddevice as sd
from loguru import logger

from audio_player import StreamPlayer
from config import TTSConfig, config_manager
from pydantic_gradio_builder import PydanticGradioBuilder

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
        gr.Info(status_msg)
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

            return str(temp_file_path)  # Gradio需要字符串路径
        else:
            return None

    except Exception as e:
        error_msg = f"❌ 播放失败: {str(e)}"
        logger.error(error_msg)
        gr.Error(error_msg)
        return None


def create_config_interface():
    """创建配置界面"""
    # 使用新的构建器
    builder = PydanticGradioBuilder(TTSConfig)
    # 从文件重新加载配置，确保显示最新值
    config_manager.load_config()
    current_config = config_manager.config

    with gr.Blocks() as config_tab:
        # 创建字段到组件的映射
        field_components = {}

        # 简单的垂直布局，按模型字段顺序排列
        for field_name in builder.field_names:
            current_value = getattr(current_config, field_name)
            component = builder.create_component(field_name, current_value)
            field_components[field_name] = component

        # 按照pydantic模型字段顺序排列组件
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
            outputs=[audio_output],
        )

        text_input.submit(
            fn=play_audio_with_params,
            inputs=play_inputs,
            outputs=[audio_output],
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
    )

    return demo


def main():
    """主函数"""
    try:
        # 初始化时打印设备信息
        logger.info("初始化音频设备...")
        logger.info(f"当前 API URL: {config_manager.config.api_url}")
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
