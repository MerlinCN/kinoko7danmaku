<div align="center">

<img src="https://socialify.git.ci/MerlinCN/kinoko7danmaku/image?description=1&forks=1&issues=1&language=1&name=1&owner=1&stargazers=1&theme=Light" alt="kinoko7danmaku" width="640" height="320" />


[![Build and Release](https://github.com/MerlinCN/kinoko7danmaku/actions/workflows/pyinstaller.yml/badge.svg)](https://github.com/MerlinCN/kinoko7danmaku/actions/workflows/pyinstaller.yml)

</div>

## 简介

基于 PySide6 + qfluentwidgets 的 B 站直播弹幕姬，支持多种 TTS 服务，实时将弹幕、礼物、舰长等信息转为语音播报。


## 环境要求

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (推荐的Python包管理器)


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
uv sync # 仅安装
uv sync --all-extras # 开发
```

### 4. 运行程序

```bash
# 使用 uv
uv run src/main.py

# 或直接使用 python
python src/main.py
```

启动会打开 GUI 界面：
1. **扫码登录** - 使用 B 站 APP 扫描二维码登录
2. **配置设置** - 在设置页面配置 TTS 服务、直播间房间号等
3. **开始监听** - 点击"开始监听"按钮即可开始弹幕播报

## 配置说明

启动后点击左下角"设置"即可进入：

- **B 站服务** - 配置直播间房间号、礼物阈值、弹幕开关等
- **TTS 服务** - 选择并配置 TTS 服务（MiniMax、Fish Speech、GPT-SoVITS）
- **音频播放** - 选择音频输出设备
- **别名字典** - 管理特殊词汇的发音替换规则
- **文本模板** - 自定义各类消息的播报文本

所有设置会自动保存到 `data/config.json` 文件中。



## 项目结构

```
kinoko7danmaku/
├── src/
│   ├── bilibili/          # B站直播间连接服务
│   │   ├── bili_service.py    # 直播间事件监听
│   │   └── __init__.py
│   ├── core/              # 核心功能模块
│   │   ├── const.py           # 常量定义
│   │   ├── player.py          # 音频播放器
│   │   ├── qconfig.py         # Qt 配置管理
│   │   └── __init__.py
│   ├── gui/               # GUI 界面
│   │   ├── components/        # 可复用组件
│   │   │   ├── alias_dict_card.py      # 别名字典卡片
│   │   │   ├── danmaku_control_card.py # 弹幕控制卡片
│   │   │   ├── message_display_card.py # 消息显示卡片
│   │   │   ├── user_info_card.py       # 用户信息卡片
│   │   │   └── ...
│   │   ├── view/              # 视图页面
│   │   │   ├── main.py            # 主窗口
│   │   │   ├── settings.py        # 设置界面
│   │   │   ├── audio_test.py      # 音频测试界面
│   │   │   └── __init__.py
│   │   └── __init__.py
│   ├── models/            # 数据模型
│   │   ├── bilibili.py        # B站消息模型
│   │   ├── minimax.py         # MiniMax API 模型
│   │   ├── device.py          # 音频设备模型
│   │   ├── service.py         # 服务类型枚举
│   │   └── __init__.py
│   ├── tts_service/       # TTS 服务适配器
│   │   ├── base.py            # TTS 服务基类
│   │   ├── minimax.py         # MiniMax 适配器
│   │   ├── fish_speech.py     # Fish Speech 适配器
│   │   ├── gpt_sovits.py      # GPT-SoVITS 适配器
│   │   └── __init__.py
│   └── main.py            # 程序入口
|
├── resource/              # 资源文件
│   ├── qss/                   # 样式表
│   └── icon.ico               # 应用图标
├── config.toml            # 配置文件（运行时自动生成）
└── pyproject.toml         # 项目依赖定义
```

## 开发指南

### 添加新的 TTS 服务

1. 在 `src/tts_service/` 创建新的适配器类，继承 `TTSService`
2. 实现 `text_to_speech` 异步方法（返回 WAV 格式音频数据）
3. 在 `src/models/service.py` 的 `ServiceType` 枚举中添加服务类型
4. 在 `src/core/qconfig.py` 添加配置类（继承 `ConfigItem`）
5. 在 `src/tts_service/__init__.py` 的 `get_tts_service()` 中注册服务
6. 在 `src/gui/view/settings.py` 添加对应的设置卡片

**注意事项：**
- 参数默认值使用 `None`，在函数体内从配置读取
- 确保返回的音频格式为 WAV（PCM 16-bit）

### 添加新的 GUI 组件

1. 在 `src/gui/components/` 创建新组件
2. 继承 qfluentwidgets 的相应基类（如 `CardWidget`、`SettingCard`）
3. 实现 UI 布局和信号槽连接
4. 在 `__init__.py` 中导出组件

### 代码规范

- **类型注解**：所有函数必须添加类型注解
- **文档字符串**：使用中文编写 docstring
- **导入顺序**：标准库 → 第三方库 → 本地模块
- **代码检查**：使用 `ruff` 进行格式化和检查

```bash
# 检查单个文件
uv run ruff check --fix src/path/to/file.py

# 检查整个项目（谨慎使用，建议先询问）
uv run ruff check --fix src/
```

## 支持与贡献

觉得好用可以给这个项目点个 Star 或者去 [爱发电](https://afdian.net/a/MerlinCN) 投喂我。

有意见或建议欢迎提交 Issues 和 Pull Requests。

## 许可证

本项目使用 [GNU AGPLv3](https://choosealicense.com/licenses/agpl-3.0/) 作为开源许可证。
