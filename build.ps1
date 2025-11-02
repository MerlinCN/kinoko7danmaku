# PowerShell 打包脚本
# 使用 PyInstaller 打包 Kinoko7Danmaku 项目

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Kinoko7Danmaku PyInstaller 打包工具" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 清理之前的构建产物
Write-Host "[1/4] 清理旧的构建文件..." -ForegroundColor Yellow
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
Write-Host "[2/4] 运行 PyInstaller..." -ForegroundColor Yellow
uv run pyinstaller kinoko7danmaku.spec

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "✗ 打包失败！" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[3/4] 复制资源文件和配置..." -ForegroundColor Yellow

# 复制 resource 目录到根目录
if (Test-Path "resource") {
    Copy-Item "resource" "dist/弹幕姬/" -Recurse -Force
    Write-Host "  ✓ 已复制 resource 目录" -ForegroundColor Green
}


Write-Host ""
Write-Host "[4/4] 打包完成！" -ForegroundColor Green
Write-Host ""
Write-Host "可执行文件位置：" -ForegroundColor Cyan
Write-Host "  dist/弹幕姬/弹幕姬.exe" -ForegroundColor White
Write-Host ""
Write-Host "使用方法：" -ForegroundColor Cyan
Write-Host "  1. 进入 dist/弹幕姬/ 目录" -ForegroundColor White
Write-Host "  2. 双击 弹幕姬.exe 运行" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
