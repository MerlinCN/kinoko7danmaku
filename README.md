<div align="center">

<img src="https://socialify.git.ci/MerlinCN/kinoko7danmaku/image?description=1&forks=1&issues=1&language=1&name=1&owner=1&stargazers=1&theme=Light" alt="kinoko7danmaku" width="640" height="320" />


[![Build and Release](https://github.com/MerlinCN/kinoko7danmaku/actions/workflows/pyinstaller.yml/badge.svg)](https://github.com/MerlinCN/kinoko7danmaku/actions/workflows/pyinstaller.yml)

</div>

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

## 克隆

直接克隆项目即可：

```bash
git clone https://github.com/MerlinCN/kinoko7danmaku.git
cd kinoko7danmaku
```

## 安装环境

### 使用 uv (推荐)

首先安装 uv：

```bash
# 方式1: 使用官方安装脚本 (推荐)
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 方式2: 使用 pip 安装
pip install uv
```

然后安装项目依赖：

```bash
uv sync
```

### 使用 pip

如果你更喜欢使用传统的 pip：

```bash
pip install -e .
```

## 开始使用

```bash
# 使用 uv
uv run python src/main.py

# 或者使用 python
python src/main.py
```

启动后访问：http://127.0.0.1:7860

注意工作目录要在根目录下

## 配置说明

项目使用 `config.json` 文件进行配置，首次运行会自动生成默认配置。主要配置项说明：

### 直播间配置
- `room_id` (int): 直播间的房间号，默认为 `213`。支持短号和长号。
- `gift_threshold` (int): 礼物触发阈值（单位：元）。只有当收到的礼物价值大于或等于这个值时，才会触发语音播报。默认值为 `5`。

### TTS API 配置
- `api_url` (str): TTS API 服务地址，默认为 `"http://localhost:8080/v1/tts"`。支持 Fish-Speech API 格式。

### 功能开关
- `normal_danmaku_on` (bool): 普通弹幕触发开关。默认为 `False`。
- `guard_on` (bool): 舰长功能触发开关。默认为 `True`。
- `super_chat_on` (bool): 醒目留言功能触发开关。默认为 `True`。
- `welcome_on` (bool): 启动成功后语音播报开关。默认为 `True`。

### 文本处理
- `alias` (dict): 别名字典。用于替换某些特定的词语以改善发音。例如：`{"Merlin": "么林"}`。默认包含 `{"Merlin": "么林"}`。

### 文本模板
- `gift_on_text` (str): 礼物触发文本模板。默认为 `""{user_name}" 赠送了{gift_num}个{gift_name}"`。
- `danmaku_on_text` (str): 弹幕触发文本模板。默认为 `""{user_name}"说:"{message}""`。
- `guard_on_text` (str): 舰长触发文本模板。默认为 `"感谢 "{user_name}" 赠送的{guard_name}，祝你熬夜不秃头，瞎吃不长胖！"`。
- `super_chat_on_text` (str): 醒目留言触发文本模板。默认为 `""{user_name}" 发送了一条醒目留言，他说"{message}""`。

### 调试配置
- `debug` (bool): 调试模式开关。默认为 `False`。

## TTS API 服务

本项目默认使用 Fish-Speech TTS API。如果要使用别的TTS API 可以修改`play_from_text`, 欢迎PR。你可以：

### 本地部署 Fish-Speech

参考 [Fish-Speech 官方文档](https://speech.fish.audio/) 进行本地部署


### 使用在线服务

你也可以使用兼容 Fish-Speech API 格式的在线服务，在配置中修改 `api_url` 即可。

### API 参数

项目支持以下 TTS 参数的配置：
- `chunk_length`: 文本分块长度，默认 200
- `max_new_tokens`: 最大新生成 token 数，默认 1024
- `top_p`: 采样参数，默认 0.8
- `repetition_penalty`: 重复惩罚，默认 1.1
- `temperature`: 温度参数，默认 0.8

## 支持与贡献

觉得好用可以给这个项目点个 Star 或者去 [爱发电](https://afdian.net/a/MerlinCN) 投喂我。

有意见或者建议也欢迎提交 Issues 和 Pull requests。

## 许可证

本项目使用 [GNU AGPLv3](https://choosealicense.com/licenses/agpl-3.0/) 作为开源许可证。