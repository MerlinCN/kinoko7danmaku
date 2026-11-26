# PowerShell 打包脚本
# 使用 PyInstaller 打包 Kinoko7Danmaku 项目
#
# 错误上报的 DSN 在打包时注入 resource/telemetry.json：
#   $env:SENTRY_DSN = "https://..."
#   ./build.ps1
# 不设置时打出的 exe 不会上报错误。

param(
    [string]$SentryDsn = $env:SENTRY_DSN
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Kinoko7Danmaku PyInstaller 打包工具" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$TelemetryPath = "resource/telemetry.json"

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

# 注入错误上报配置
Write-Host "[2/4] 注入错误上报配置..." -ForegroundColor Yellow
if (Test-Path $TelemetryPath) {
    Remove-Item -Force $TelemetryPath
}
if ($SentryDsn) {
    $json = @{ sentry_dsn = $SentryDsn } | ConvertTo-Json -Compress
    $fullPath = Join-Path (Get-Location).Path $TelemetryPath
    [System.IO.File]::WriteAllText($fullPath, $json, [System.Text.UTF8Encoding]::new($false))
    Write-Host "  ✓ 已写入 $TelemetryPath" -ForegroundColor Green
}
else {
    Write-Host "  ⚠ 未提供 SENTRY_DSN，本次打包的 exe 不会上报错误" -ForegroundColor DarkYellow
}
Write-Host ""

# 运行 PyInstaller
Write-Host "[3/4] 运行 PyInstaller（单文件模式）..." -ForegroundColor Yellow
uv run pyinstaller kinoko7danmaku.spec

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "✗ 打包失败！" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[4/4] 打包完成！" -ForegroundColor Green
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
