@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ============================================
:: 抖音陪玩Agent - 一键启动脚本 (Windows)
:: 双击此文件即可启动
:: ============================================

title 抖音陪玩Agent - 启动器
color 0A

echo.
echo ╔══════════════════════════════════════════════╗
echo ║       抖音陪玩Agent - 一键启动脚本 v1.0      ║
echo ╚══════════════════════════════════════════════╝
echo.

:: ====== 配置 ======
set PORT=5002
set PROJECT_ROOT=%~dp0

:: 创建日志目录
if not exist "%PROJECT_ROOT%logs" mkdir "%PROJECT_ROOT%logs"

:: ============================================
:: 步骤 1: 检查Python
:: ============================================
echo [步骤 1/5] 检查Python环境...

python --version >nul 2>&1
if errorlevel 1 (
    echo   ✗ 未检测到Python!
    echo.
    echo   请安装Python 3.7+:
    echo   https://www.python.org/downloads/
    echo   安装时勾选 "Add Python to PATH"
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version') do set PYVER=%%v
echo   ✓ Python %PYVER% 已安装

:: 检查pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo   ✗ Pip未安装
    pause
    exit /b 1
)
echo   ✓ Pip已安装
echo.

:: ============================================
:: 步骤 2: 虚拟环境(可选)
:: ============================================
echo [步骤 2/5] 检查虚拟环境...

if not exist "%PROJECT_ROOT%venv\Scripts\activate.bat" (
    echo   正在创建虚拟环境...
    python -m venv venv >nul 2>&1
    if not errorlevel 1 (
        echo   ✓ 虚拟环境已创建: .\venv\
    ) else (
        echo   ⚠ 虚拟环境创建失败，使用全局Python
    )
) else (
    echo   ✓ 虚拟环境已存在
)
echo.

:: ============================================
:: 步骤 3: 安装依赖
:: ============================================
echo [步骤 3/5] 安装依赖包...

if not exist "%PROJECT_ROOT%requirements.txt" (
    echo   ✗ 未找到 requirements.txt
    pause
    exit /b 1
)

echo   正在安装依赖 (请耐心等待)...
echo.

pip install -r "%PROJECT_ROOT%requirements.txt" --quiet
if errorlevel 1 (
    echo   ✗ 依赖安装失败!
    echo.
    echo   尝试使用国内镜像源:
    echo   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    pause
    exit /b 1
)

echo   ✓ 依赖安装完成!
echo.

:: ============================================
:: 步骤 4: 验证模块
:: ============================================
echo [步骤 4/5] 验证关键模块...

set MODULES=flask flask_socketio mss easyocr sklearn
set MISSING=

for %%m in (%MODULES%) do (
    python -c "import %%m" >nul 2>&1
    if errorlevel 1 (
        echo   ✗ %%m 缺失
        set MISSING=!MISSING! %%m
    ) else (
        echo   ✓ %%m
    )
)

if defined MISSING (
    echo.
    echo   ⚠ 自动修复缺失模块...
    for %%m in (!MISSING!) do pip install %%m >nul 2>&1
    echo   ✓ 修复完成!
)
echo.

:: ============================================
:: 步骤 5: 启动服务
:: ============================================
echo [步骤 5/5] 启动Web服务...
echo.

if not exist "%PROJECT_ROOT%web\server.py" (
    echo   ✗ 未找到 server.py
    pause
    exit /b 1
)

echo ╔═════════════════════════════════════════╗
echo ║  抖音陪玩Agent 即将启动...              ║
echo ╠═════════════════════════════════════════╣
echo ║  访问地址: http://localhost:%PORT%       ║
echo ║  按 Ctrl+C 停止服务                     ║
echo ╚═════════════════════════════════════════╝
echo.

:: 设置编码
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

:: 启动服务器
cd /d "%PROJECT_ROOT%"
python web\server.py --port %PORT%

echo.
echo 服务已停止。
pause
