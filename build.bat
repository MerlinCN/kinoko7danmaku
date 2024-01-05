@echo off
chcp 65001

python -m pip install -r requirements.txt

REM 检测并删除 build 和 dist 文件夹
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist


REM 使用 PyInstaller 打包您的程序
pyinstaller --onefile --name=start --icon=resource/icon.ico src/main.py

REM 检查是否存在 bin 目录并复制到 build 文件夹下
xcopy /s /i bin dist\bin\



REM 压缩 build 文件夹为 danmaku.zip
REM 确保 7z 命令可以在命令行中使用
pushd dist
echo start.exe > start.bat
echo pause >> start.bat
7z a ../danmaku.zip *
popd

echo 打包和压缩完成!
pause
