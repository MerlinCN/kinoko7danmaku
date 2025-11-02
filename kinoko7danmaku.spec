# -*- mode: python ; coding: utf-8 -*-

"""PyInstaller 打包配置文件

使用方法：
    uv run pyinstaller kinoko7danmaku.spec

生成的可执行文件位于 dist/ 目录
"""

import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# 项目根目录
root_dir = Path.cwd()

# 自动收集第三方库的所有子模块
bilibili_api_hiddenimports = collect_submodules('bilibili_api')
bilibili_api_datas = collect_data_files('bilibili_api')

qfluentwidgets_hiddenimports = collect_submodules('qfluentwidgets')
qfluentwidgets_datas = collect_data_files('qfluentwidgets')

stream_gears_hiddenimports = collect_submodules('stream_gears')
stream_gears_datas = collect_data_files('stream_gears')

# 收集所有资源文件
datas = [
    # 添加 resource 目录（单文件模式会打包到临时目录）
    (str(root_dir / "resource"), "resource"),
]

# 添加第三方库的数据文件
datas += bilibili_api_datas
datas += qfluentwidgets_datas
datas += stream_gears_datas

# 隐藏导入（PyInstaller 可能检测不到的模块）
hiddenimports = [
    # PySide6 相关
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtSvg",
    # qasync
    "qasync",
    # 音频相关
    "pyaudio",
    "sounddevice",
    # 其他
    "loguru",
    "pydantic",
    "pydantic_settings",
    "aiohttp",
    "qrcode",
    "httpx",
]
# 添加自动收集的第三方库子模块
hiddenimports += bilibili_api_hiddenimports
hiddenimports += qfluentwidgets_hiddenimports
hiddenimports += stream_gears_hiddenimports

a = Analysis(
    [str(root_dir / "src" / "main.py")],  # 入口文件
    pathex=[str(root_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,  # 单文件模式：包含所有二进制文件
    a.zipfiles,  # 单文件模式：包含所有 zip 文件
    a.datas,     # 单文件模式：包含所有数据文件
    [],
    name="弹幕姬",  # 可执行文件名
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台窗口（GUI 应用）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(root_dir / "resource" / "icon.ico"),  # 应用图标
)

# 单文件模式不需要 COLLECT