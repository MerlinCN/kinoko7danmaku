# kinoko PyInstaller打包脚本 (单文件模式)
Write-Host "开始使用PyInstaller打包kinoko项目 (单文件模式)..." -ForegroundColor Green
Write-Host ""
# 确保输出目录存在 (单文件模式下，exe直接生成在此目录)
$distDir = "dist"

# 每次运行前删除dist文件夹
if (Test-Path $distDir) {
    Write-Host "正在删除旧的dist文件夹..." -ForegroundColor Yellow
    Remove-Item -Path $distDir -Recurse -Force
    Write-Host "已删除旧的dist文件夹" -ForegroundColor Gray
}

# 创建新的dist目录
New-Item -ItemType Directory -Path $distDir | Out-Null
Write-Host "已创建新的dist目录" -ForegroundColor Gray

# 构建PyInstaller命令
# 添加 --onefile 参数以生成单个可执行文件
# 关键：添加 --collect-all httpx 以确保 httpx 及其所有依赖被包含
# 添加 --hidden-import multiprocessing 确保多进程支持
$cmd = @(
    "uv",
    "run",
    "pyinstaller",
    "--onefile",
    "--clean",
    "--name=kinoko",
    "--noconfirm",
    "src/main.py"
)

# 显示命令
Write-Host "执行命令: $($cmd -join ' ')" -ForegroundColor Yellow
Write-Host ("-" * 50) -ForegroundColor Gray

# 执行打包
try {
    & $cmd[0] $cmd[1..($cmd.Length-1)]
    $exitCode = $LASTEXITCODE
    
    Write-Host ("-" * 50) -ForegroundColor Gray
    
    if ($exitCode -eq 0) {
        Write-Host "PyInstaller打包成功！" -ForegroundColor Green
        Write-Host "输出文件: $distDir\kinoko.exe" -ForegroundColor Cyan
        
        # 单文件模式下，lib、bin和node_modules文件夹需要手动复制到exe同级目录 (即 $distDir)，
        # 因为它们不会被打包进exe，而是作为外部资源
        $outputDir = "$distDir" # <-- 关键修改：单文件模式下，直接复制到dist目录
        if (Test-Path "bin") {
            Copy-Item -Path "bin" -Destination $outputDir -Recurse -Force
            Write-Host "已复制bin文件夹到输出目录" -ForegroundColor Gray
        }
        # 创建启动脚本
        Write-Host "正在创建启动脚本..." -ForegroundColor Yellow
        
        # 创建 start.bat
        @"
@echo off
chcp 65001 >nul
title kinoko

echo 正在启动kinoko...
echo.

kinoko.exe

if %errorlevel% neq 0 (
    echo.
    echo 程序异常退出，错误代码：%errorlevel%
    echo.
)

echo.
pause
"@ | Out-File -FilePath "$distDir\启动点这个.bat" -Encoding UTF8
        Write-Host "已创建 启动脚本" -ForegroundColor Gray

        # 清理临时文件
        if (Test-Path "build") {
            Remove-Item -Path "build" -Recurse -Force
            Write-Host "已清理临时构建文件" -ForegroundColor Gray
        }
        if (Test-Path "kinoko.spec") {
            Remove-Item -Path "kinoko.spec" -Force
            Write-Host "已清理spec文件" -ForegroundColor Gray
        }

        # 创建版本号（使用当前日期和时间）
        $version = Get-Date -Format "yyyyMMdd_HHmmss"
        $zipName = "kinoko_v$version.zip"
        
        # 压缩dist目录
        Write-Host "正在创建发布包..." -ForegroundColor Yellow
        try {
            # 使用PowerShell的Compress-Archive命令
            Compress-Archive -Path "$distDir\*" -DestinationPath $zipName -Force
            Write-Host "发布包创建成功: $zipName" -ForegroundColor Green
        } catch {
            Write-Host "创建发布包失败: $($_.Exception.Message)" -ForegroundColor Red
        }
    } else {
        Write-Host "PyInstaller打包失败，返回码: $exitCode" -ForegroundColor Red
    }
} catch {
    Write-Host "执行过程中发生错误: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "按任意键继续..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
