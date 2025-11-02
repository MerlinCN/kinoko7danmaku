# PowerShell 打包脚本
# 使用 PyInstaller 打包 Kinoko7Danmaku 项目

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Kinoko7Danmaku PyInstaller 打包工具" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 清理之前的构建产物
Write-Host "[1/3] 清理旧的构建文件..." -ForegroundColor Yellow
if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
    Write-Host "  ✓ 已删除 build 目录" -ForegroundColor Green
}
if (Test-Path "dist") {
    Remove-Item -Recurse -Force "dist"
    Write-Host "  ✓ 已删除 dist 目录" -ForegroundColor Green
}
Write-Host ""

# 运行 PyInstaller
Write-Host "[2/3] 运行 PyInstaller（单文件模式）..." -ForegroundColor Yellow
uv run pyinstaller kinoko7danmaku.spec

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "✗ 打包失败！" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[3/3] 打包完成！" -ForegroundColor Green
Write-Host ""
Write-Host "可执行文件位置：" -ForegroundColor Cyan
Write-Host "  dist/弹幕姬.exe" -ForegroundColor White
Write-Host ""
Write-Host "使用方法：" -ForegroundColor Cyan
Write-Host "  直接双击 弹幕姬.exe 运行" -ForegroundColor White
Write-Host ""
Write-Host "注意：" -ForegroundColor Yellow
Write-Host "  - 单文件模式首次启动较慢（需要解压）" -ForegroundColor White
Write-Host "  - 所有资源已打包进 exe 文件" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
