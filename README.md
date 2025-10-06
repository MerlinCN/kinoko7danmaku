<div align="center">

<img src="https://socialify.git.ci/MerlinCN/kinoko7danmaku/image?description=1&forks=1&issues=1&language=1&name=1&owner=1&stargazers=1&theme=Light" alt="kinoko7danmaku" width="640" height="320" />


[![Build and Release](https://github.com/MerlinCN/kinoko7danmaku/actions/workflows/pyinstaller.yml/badge.svg)](https://github.com/MerlinCN/kinoko7danmaku/actions/workflows/pyinstaller.yml)

</div>

## 简介

B站直播间弹幕姬，支持多种 TTS 服务，实时将弹幕、礼物、舰长等信息转为语音播报。

## 环境要求

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (推荐的Python包管理器)

## 依赖项目

### B站登录认证 - biliup-rs

本项目的B站登录功能依赖于 [biliup-rs](https://github.com/ForgQi/biliup-rs) 项目。

- **Windows**: 使用 `bin/biliup.exe`
- **macOS (ARM64)**: 使用 `bin/biliup-aarch64-macos`

首次使用时，程序会自动调用 biliup 进行B站账号登录，登录信息会保存在 `cookies.json` 文件中。后续启动会自动续期登录状态。

感谢 [ForgQi/biliup-rs](https://github.com/ForgQi/biliup-rs) 项目提供的登录支持！

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/MerlinCN/kinoko7danmaku.git
cd kinoko7danmaku
```

### 2. 安装 uv (推荐)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 或使用 pip 安装
pip install uv
```

### 3. 安装依赖

```bash
uv sync
```

### 4. 配置项目

复制配置示例文件并修改：

```bash
cp config.example.toml config.toml
```

编辑 `config.toml`，配置你的 TTS 服务和直播间信息。

### 5. 运行程序

```bash
# 使用 uv
uv run python src/main.py

# 或直接使用 python
python src/main.py
```

## 配置说明

项目使用 `config.toml` 文件进行配置。配置文件采用 TOML 格式，支持类型安全的配置管理。

### 直播间配置 `[bili_service]`

```toml
[bili_service]
room_id = 213                    # 直播间房间号（支持短号/长号）
gift_threshold = 5               # 礼物触发阈值（元）
normal_danmaku_on = true         # 普通弹幕触发开关
guard_on = true                  # 舰长触发开关
super_chat_on = true             # 醒目留言触发开关
welcome_on = true                # 启动语音播报开关
debug = false                    # 调试模式

# 文本模板（支持变量替换）
gift_on_text = '"{user_name}" 赠送了{gift_num}个{gift_name}'
danmaku_on_text = '"{user_name}"说:"{message}"'
guard_on_text = '感谢 "{user_name}" 赠送的{guard_name}，祝你熬夜不秃头，瞎吃不长胖！'
super_chat_on_text = '"{user_name}" 发送了一条醒目留言，他说"{message}"'
```

### 别名配置 `[bili_service.alias]`

用于替换特定词语以改善发音效果：

```toml
[bili_service.alias]
Merlin = "么林"
Claude = "克劳德"
```

### TTS 服务配置

项目支持多种 TTS 服务，可在 `[tts_service]` 中指定激活的服务：

```toml
[tts_service]
active = ["minimax"]  # 可选: fish_speech, gpt_sovits, minimax
```

#### MiniMax TTS（推荐）

高质量云端 TTS 服务，支持多语言、多音色、情感表达：

```toml
[tts_service.minimax]
api_url = "https://api.minimaxi.chat/v1/t2a_v2"
api_key = "your_api_key_here"       # 在 minimax.ai 获取
model = "speech-2.5-hd-preview"     # 模型版本
voice_id = "audiobook_male_1"       # 音色ID（300+可选）
speed = 1.0                         # 语速 (0.5-2.0)
vol = 1.0                           # 音量 (0.0-2.0)
pitch = 0                           # 音调 (-12-12)
```

**获取 API Key:**
1. 访问 [MiniMax 开放平台](https://www.minimaxi.com/platform_overview)
2. 注册并创建应用
3. 获取 API Key 和 Group ID

#### Fish Speech

本地部署的高质量开源 TTS：

```toml
[tts_service.fish_speech]
api_url = "http://localhost:28080/v1/tts"
```

**部署方法：** 参考 [Fish-Speech 官方文档](https://speech.fish.audio/)

#### GPT-SoVITS

支持声音克隆的本地 TTS：

```toml
[tts_service.gpt_sovits]
api_url = "http://localhost:19872"
sovits_model = "SoVITS_weights_v4/model.pth"
gpt_model = "GPT_weights_v4/model.ckpt"
text_lang = "Multilingual Mixed"
ref_audio_path = "ref_audio/ref.wav"
ref_text = "参考文本"
ref_text_lang = "Chinese"
# ... 更多参数见 config.example.toml
```

**部署方法：** 参考 [GPT-SoVITS 项目](https://github.com/RVC-Boss/GPT-SoVITS)

## 功能特性

- ✨ 支持多种 TTS 服务（MiniMax、Fish Speech、GPT-SoVITS）
- 🎯 灵活的触发条件配置
- 📝 自定义文本模板和别名
- 🔊 音频设备选择
- 🚀 基于 Pydantic 的类型安全配置
- 🔄 自动重连和错误重试
- 📊 详细的日志记录

## 项目结构

```
kinoko7danmaku/
├── src/
│   ├── bilibili/          # B站直播间连接
│   ├── config/            # 配置管理
│   ├── player/            # 音频播放器
│   ├── schema/            # 数据模型
│   ├── tts_service/       # TTS 服务适配器
│   └── main.py            # 主程序入口
├── bin/                   # biliup 可执行文件
├── config.toml            # 配置文件（需自行创建）
├── config.example.toml    # 配置示例
└── pyproject.toml         # 项目依赖
```

## 开发指南

### 添加新的 TTS 服务

1. 在 `src/tts_service/` 创建新的适配器类
2. 继承 `TTSService` 基类
3. 实现 `text_to_speech` 方法
4. 在 `src/schema/const.py` 添加服务类型枚举
5. 在 `src/config/setting.py` 添加配置类
6. 在 `src/tts_service/__init__.py` 注册服务

### 代码规范

- 使用 `ruff` 进行代码检查和格式化
- 使用类型注解
- 添加 docstring 文档

```bash
# 运行代码检查
uv run ruff check --fix src/
```

## 常见问题

### 1. 找不到输出设备

检查系统音频设备，可在 `config.toml` 中配置：

```toml
[setting]
player_device = "your_device_name"
```

### 2. TTS 请求超时

- 检查网络连接
- 确认 API 服务可访问
- 增加超时时间配置

### 3. 音频播放卡顿

- 检查系统音频驱动
- 尝试更换输出设备
- 降低 TTS 并发数

## 支持与贡献

觉得好用可以给这个项目点个 Star 或者去 [爱发电](https://afdian.net/a/MerlinCN) 投喂我。

有意见或建议欢迎提交 Issues 和 Pull Requests。

## 许可证

本项目使用 [GNU AGPLv3](https://choosealicense.com/licenses/agpl-3.0/) 作为开源许可证。
