import os
import tempfile

import gradio as gr
import gradio.themes as themes
from loguru import logger

from audio_player import StreamPlayer
from config import config_manager

# 全局 StreamPlayer 实例
stream_player = StreamPlayer()

# 存储临时文件列表用于清理
temp_files = []


def cleanup_temp_file(file_path):
    """清理临时文件"""
    try:
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)
            if file_path in temp_files:
                temp_files.remove(file_path)
    except Exception as e:
        logger.warning(f"清理临时文件失败: {e}")


def cleanup_all_temp_files():
    """清理所有临时文件"""
    for file_path in temp_files.copy():
        cleanup_temp_file(file_path)


# 配置相关函数
def get_current_config():
    """获取当前配置"""
    config = config_manager.config
    return {
        "room_id": config.room_id,
        "gift_threshold": config.gift_threshold,
        "api_url": config.api_url,
        "api_mode": config.api_mode,
        "normal_danmaku_on": config.normal_danmaku_on,
        "guard_on": config.guard_on,
        "super_chat_on": config.super_chat_on,
        "voice_name": config.voice_name,
        "voice_channel": config.voice_channel,
        "target_speed": config.target_speed,
        "alias": config.alias,
        "debug": config.debug,
    }


def format_alias_for_display(alias_dict):
    """将别名字典格式化为显示文本"""
    if not alias_dict:
        return ""
    return "\n".join([f"{k}={v}" for k, v in alias_dict.items()])


def parse_alias_from_text(alias_text):
    """从文本解析别名字典"""
    alias_dict = {}
    if not alias_text.strip():
        return alias_dict

    for line in alias_text.strip().split("\n"):
        line = line.strip()
        if "=" in line:
            key, value = line.split("=", 1)
            alias_dict[key.strip()] = value.strip()
    return alias_dict


def create_alias_row(key="", value="", row_id=0):
    """创建一个别名配置行"""
    with gr.Row():
        key_input = gr.Textbox(
            label="",
            placeholder="输入原词",
            value=key,
            scale=2,
            container=False,
            elem_id=f"alias_key_{row_id}",
        )

        value_input = gr.Textbox(
            label="",
            placeholder="输入替换词",
            value=value,
            scale=2,
            container=False,
            elem_id=f"alias_value_{row_id}",
        )

        delete_btn = gr.Button(
            "🗑️",
            size="sm",
            scale=0,
            variant="secondary",
            elem_id=f"alias_delete_{row_id}",
        )

    return key_input, value_input, delete_btn


def create_alias_interface(current_config):
    """创建别名配置界面"""
    alias_dict = current_config["alias"]
    alias_items = list(alias_dict.items())

    # 最多支持10个别名配置
    max_alias_rows = 10

    # 存储所有别名输入组件
    alias_key_inputs = []
    alias_value_inputs = []
    alias_delete_btns = []
    alias_rows = []

    gr.Markdown("#### 📝 别名配置")

    # 添加按钮和状态管理
    initial_visible_count = max(len(alias_items), 1)  # 至少显示1行
    visible_count_state = gr.State(value=initial_visible_count)

    with gr.Row():
        add_alias_btn = gr.Button("➕ 添加新规则", variant="secondary", size="sm")
        gr.Markdown("点击添加按钮来创建新的词语替换规则")

    # 创建别名输入行
    for i in range(max_alias_rows):
        key_value = alias_items[i][0] if i < len(alias_items) else ""
        value_value = alias_items[i][1] if i < len(alias_items) else ""
        visible = i < initial_visible_count

        with gr.Row(visible=visible) as alias_row:
            key_input = gr.Textbox(
                label="原词", value=key_value, placeholder="输入要替换的原词", scale=2
            )

            value_input = gr.Textbox(
                label="替换词", value=value_value, placeholder="输入替换后的词", scale=2
            )

            delete_btn = gr.Button("🗑️ 删除", variant="secondary", size="sm", scale=0)

        alias_key_inputs.append(key_input)
        alias_value_inputs.append(value_input)
        alias_delete_btns.append(delete_btn)
        alias_rows.append(alias_row)

    # 添加使用说明
    gr.Markdown("""
    **使用说明：**
    - 在"原词"中输入需要替换的词语
    - 在"替换词"中输入替换后的词语
    - 例如：原词填写"Merlin"，替换词填写"么林"
    - 空行会被自动忽略
    """)

    def add_new_row(current_visible_count):
        """添加新行"""
        new_count = min(current_visible_count + 1, max_alias_rows)

        updates = []
        for i in range(max_alias_rows):
            updates.append(gr.update(visible=i < new_count))

        return new_count, *updates

    def delete_row(row_index):
        """删除指定行"""

        def delete_func(current_visible_count):
            # 清空该行
            key_update = gr.update(value="")
            value_update = gr.update(value="")

            # 如果删除的是最后一行且不是第一行，则减少可见行数
            if row_index == current_visible_count - 1 and current_visible_count > 1:
                new_count = current_visible_count - 1
                row_update = gr.update(visible=False)
            else:
                new_count = current_visible_count
                row_update = gr.update()

            return new_count, key_update, value_update, row_update

        return delete_func

    # 绑定添加按钮事件
    add_alias_btn.click(
        fn=add_new_row,
        inputs=[visible_count_state],
        outputs=[visible_count_state] + alias_rows,
    )

    # 绑定删除按钮事件
    for i, delete_btn in enumerate(alias_delete_btns):
        delete_btn.click(
            fn=delete_row(i),
            inputs=[visible_count_state],
            outputs=[
                visible_count_state,
                alias_key_inputs[i],
                alias_value_inputs[i],
                alias_rows[i],
            ],
        )

    return alias_key_inputs, alias_value_inputs


def collect_alias_data(alias_key_inputs, alias_value_inputs):
    """收集所有别名数据"""
    alias_dict = {}
    for i in range(len(alias_key_inputs)):
        key = alias_key_inputs[i] if isinstance(alias_key_inputs[i], str) else ""
        value = alias_value_inputs[i] if isinstance(alias_value_inputs[i], str) else ""
        key = key.strip()
        value = value.strip()
        if key and value:
            alias_dict[key] = value
    return alias_dict


def update_all_config(
    room_id,
    gift_threshold,
    api_url,
    api_mode,
    normal_danmaku_on,
    guard_on,
    super_chat_on,
    voice_name,
    voice_channel,
    target_speed,
    debug,
    *alias_inputs,  # 别名输入框的值
):
    """更新所有配置"""
    try:
        # 收集别名数据 - 输入是按照 key1, value1, key2, value2, ... 的顺序
        alias_dict = {}
        for i in range(0, len(alias_inputs), 2):
            if i + 1 < len(alias_inputs):
                key = alias_inputs[i].strip() if alias_inputs[i] else ""
                value = alias_inputs[i + 1].strip() if alias_inputs[i + 1] else ""
                if key and value:
                    alias_dict[key] = value

        # 验证必需字段
        if not api_url.strip():
            gr.Error("API URL 不能为空")
            return get_current_config()

        if room_id <= 0:
            gr.Error("房间号必须大于0")
            return get_current_config()

        # 更新配置
        success = config_manager.update_config(
            room_id=room_id,
            gift_threshold=gift_threshold,
            api_url=api_url.strip(),
            api_mode=api_mode,
            normal_danmaku_on=normal_danmaku_on,
            guard_on=guard_on,
            super_chat_on=super_chat_on,
            voice_name=voice_name.strip(),
            voice_channel=voice_channel,
            target_speed=target_speed,
            alias=alias_dict,
            debug=debug,
        )

        if success:
            gr.Info("配置已成功保存")
            return get_current_config()
        else:
            gr.Error("保存配置失败")
            return get_current_config()

    except Exception as e:
        gr.Error(f"更新失败: {str(e)}")
        return get_current_config()


def reset_config():
    """重置配置为默认值"""
    try:
        success = config_manager.reset_to_default()
        if success:
            gr.Info("配置已重置为默认值")
            return get_current_config()
        else:
            gr.Error("重置配置失败")
            return get_current_config()
    except Exception as e:
        gr.Error(f"重置失败: {str(e)}")
        return get_current_config()


async def play_audio_with_params(
    text: str,
    device_choice: str,
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
        if device_choice != "默认设备":
            device_index = int(device_choice.split("[")[1].split("]")[0])
            stream_player.set_output_device(device_index)

        logger.info(f"开始播放音频: {text}")

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
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            temp_file.write(audio_data)
            temp_file.close()
            temp_files.append(temp_file.name)  # 添加到临时文件列表
            return status_msg, temp_file.name
        else:
            return status_msg, None

    except Exception as e:
        error_msg = f"❌ 播放失败: {str(e)}"
        logger.error(error_msg)
        return error_msg, None


def get_device_choices():
    """获取设备选择列表"""
    devices = stream_player.get_output_devices()
    choices = ["默认设备"]

    for device in devices:
        name = f"[{device['index']}] {device['name']}"
        if device["is_default"]:
            name += " (默认)"
        choices.append(name)

    return choices


def create_config_interface():
    """创建配置界面"""
    with gr.Blocks() as config_tab:
        current_config = get_current_config()

        with gr.Row():
            # 左侧：主要配置
            with gr.Column(scale=2):
                gr.Markdown("#### 🏠 直播间配置")
                with gr.Group():
                    room_id_input = gr.Number(
                        label="房间号",
                        value=current_config["room_id"],
                        precision=0,
                        info="直播间房间号",
                    )

                    gift_threshold_input = gr.Number(
                        label="礼物阈值（元）",
                        value=current_config["gift_threshold"],
                        precision=0,
                        info="≥这个值（单位：元）才会触发礼物",
                    )

                gr.Markdown("#### 🌐 API 配置")
                with gr.Group():
                    api_url_input = gr.Textbox(
                        label="API 地址",
                        value=current_config["api_url"],
                        placeholder="http://localhost:8080/v1/tts",
                        info="TTS API 服务地址",
                    )

                    api_mode_input = gr.Radio(
                        label="API 模式",
                        choices=["bert-vits", "gpt-sovits"],
                        value=current_config["api_mode"],
                        info="API模式选择",
                    )

                gr.Markdown("#### 🎵 语音配置")
                with gr.Group():
                    voice_name_input = gr.Textbox(
                        label="模型名",
                        value=current_config["voice_name"],
                        info="语音模型名称",
                    )

                    voice_channel_input = gr.Number(
                        label="声道",
                        value=current_config["voice_channel"],
                        precision=0,
                        info="默认-1为系统输出，如果有声卡，可以自行修改",
                    )

                    target_speed_input = gr.Slider(
                        label="合成语速",
                        minimum=0.5,
                        maximum=2.0,
                        value=current_config["target_speed"],
                        step=0.1,
                        info="合成语速设置",
                    )

            # 右侧：开关和高级配置
            with gr.Column(scale=1):
                gr.Markdown("#### 🔘 触发开关")
                with gr.Group():
                    normal_danmaku_on_input = gr.Checkbox(
                        label="普通弹幕触发",
                        value=current_config["normal_danmaku_on"],
                        info="普通弹幕是否触发",
                    )

                    guard_on_input = gr.Checkbox(
                        label="舰长触发",
                        value=current_config["guard_on"],
                        info="舰长是否触发",
                    )

                    super_chat_on_input = gr.Checkbox(
                        label="醒目留言触发",
                        value=current_config["super_chat_on"],
                        info="醒目留言是否触发",
                    )

                # 别名配置区域
                alias_key_inputs, alias_value_inputs = create_alias_interface(
                    current_config
                )

                gr.Markdown("#### 🐛 调试配置")
                with gr.Group():
                    debug_input = gr.Checkbox(
                        label="调试模式",
                        value=current_config["debug"],
                        info="是否开启调试模式，不开启就行了",
                    )

        # 操作按钮
        with gr.Row():
            save_btn = gr.Button("💾 保存所有配置", variant="primary", scale=2)
            reset_btn = gr.Button("🔄 重置默认", variant="secondary", scale=1)

        gr.Markdown("#### 💡 使用说明")
        gr.Markdown("""
        - **房间号**: 要监听的直播间房间号
        - **礼物阈值**: 只有价值达到这个金额的礼物才会触发语音
        - **API配置**: TTS服务的地址和模式
        - **触发开关**: 控制哪些类型的消息会触发语音
        - **别名配置**: 替换特定词语，每行设置一个原词和替换词
        - **语音配置**: 控制语音模型和播放参数
        - 修改配置后点击保存即可生效，无需重启程序
        """)

        # 基础配置输入组件列表
        basic_config_inputs = [
            room_id_input,
            gift_threshold_input,
            api_url_input,
            api_mode_input,
            normal_danmaku_on_input,
            guard_on_input,
            super_chat_on_input,
            voice_name_input,
            voice_channel_input,
            target_speed_input,
            debug_input,
        ]

        # 构建完整的输入列表（基础配置 + 别名输入）
        all_inputs = basic_config_inputs.copy()
        for i in range(len(alias_key_inputs)):
            all_inputs.append(alias_key_inputs[i])
            all_inputs.append(alias_value_inputs[i])

        # 配置输出组件（用于更新界面显示）
        def update_config_display(config_dict):
            """更新配置显示"""
            basic_outputs = [
                config_dict["room_id"],
                config_dict["gift_threshold"],
                config_dict["api_url"],
                config_dict["api_mode"],
                config_dict["normal_danmaku_on"],
                config_dict["guard_on"],
                config_dict["super_chat_on"],
                config_dict["voice_name"],
                config_dict["voice_channel"],
                config_dict["target_speed"],
                config_dict["debug"],
            ]

            # 添加别名输出
            alias_items = list(config_dict["alias"].items())
            alias_outputs = []
            for i in range(len(alias_key_inputs)):
                if i < len(alias_items):
                    alias_outputs.append(alias_items[i][0])  # key
                    alias_outputs.append(alias_items[i][1])  # value
                else:
                    alias_outputs.append("")  # empty key
                    alias_outputs.append("")  # empty value

            return basic_outputs + alias_outputs

        # 绑定保存事件
        save_btn.click(
            fn=update_all_config,
            inputs=all_inputs,
            outputs=all_inputs,
        )

        # 绑定重置事件
        def handle_reset():
            config_dict = reset_config()
            config_outputs = update_config_display(config_dict)
            return config_outputs

        reset_btn.click(fn=handle_reset, outputs=all_inputs)

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
                    choices=get_device_choices(),
                    value="默认设备",
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
            return gr.Dropdown(choices=get_device_choices())

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
