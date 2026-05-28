<div align="center">

<img src="https://socialify.git.ci/MerlinCN/kinoko7danmaku/image?description=1&forks=1&issues=1&language=1&name=1&owner=1&stargazers=1&theme=Light" alt="kinoko7danmaku" width="640" height="320" />

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python)](https://www.python.org/)
[![Build and Release](https://github.com/MerlinCN/kinoko7danmaku/actions/workflows/pyinstaller.yml/badge.svg)](https://github.com/MerlinCN/kinoko7danmaku/actions/workflows/pyinstaller.yml)
[![Release](https://img.shields.io/github/v/release/MerlinCN/kinoko7danmaku)](https://github.com/MerlinCN/kinoko7danmaku/releases)

</div>

基于 PySide6 的 B 站直播弹幕姬，实时将弹幕、礼物、SC、舰长等消息转为语音播报。

## 特性

- **多 TTS 引擎** — 支持 MiniMax、Fish Speech、GPT-SoVITS、Piper、Edge 五种语音服务
- **实时监控** — 弹幕 / 礼物 / SC / 舰长 / 醒目留言实时捕获与播报
- **礼物合并** — 短时间内的连续礼物自动合并播报，避免刷屏
- **别名字典** — 支持特殊词汇的自定义发音替换
- **文本模板** — 各类消息的播报文案可自由定制
- **音频测试** — 内置 TTS 试听页面，支持 WAV / MP3 格式
- **扫码登录** — 通过 B 站 APP 扫码安全登录
- **跨平台** — 提供 Windows 可执行文件，macOS / Linux 可从源码运行

## 截图

![主界面](img/image-20251102121451987.png)

![设置页面](img/image-20251102121622061.png)

## 快速开始

### 环境要求

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)（推荐包管理器）

### 安装 & 运行

```bash
git clone https://github.com/MerlinCN/kinoko7danmaku.git
cd kinoko7danmaku
uv sync
uv run src/main.py
```

启动后：
1. 点击「登录」用 B 站 APP 扫码
2. 在设置页面配置 TTS 服务与直播间房间号
3. 点击「开始监听」

### Windows 用户

直接下载 [Releases](https://github.com/MerlinCN/kinoko7danmaku/releases) 中的 `Kinoko7Danmaku.exe`，无需安装 Python。

## 支持的 TTS 服务

| 服务 | 说明 | 需要 API Key |
|------|------|:---:|
| MiniMax | 高品质云端语音合成 | ✅ |
| Fish Speech | 开源语音合成 | 自部署 |
| GPT-SoVITS | 少样本语音克隆 | 自部署 |
| Piper | 本地离线 TTS | 自部署 |
| Edge | 微软免费 TTS | ❌ |

## 设置

所有配置在 GUI 设置页面中完成，包括：

- **B 站服务** — 直播间房间号、弹幕开关、礼物阈值
- **TTS 服务** — 选择引擎及对应参数（语速、音色等）
- **音频输出** — 输出设备选择
- **别名字典** — 自定义词汇发音替换
- **文本模板** — 各类消息的播报文案

配置自动保存至 `~/.kinoko7danmaku/config.json`。

## 支持与贡献

觉得好用可以给项目点个 Star，或者去 [爱发电](https://afdian.net/a/MerlinCN) 投喂我。

有意见或建议欢迎提交 Issues 和 Pull Requests。

感谢以下贡献者：

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/zjp-shadow">
        <img src="https://avatars.githubusercontent.com/zjp-shadow?v=4" width="80px;" alt="shadow"/><br />
        <sub><b>shadow</b></sub>
      </a>
    </td>
  </tr>
</table>

## 许可证

[GNU AGPL v3](LICENSE) © MerlinCN
