@echo off
chcp 65001 >nul
title 抖音陪玩Agent - 快速启动

:: ============================================
:: 抖音陪玩Agent - 快速启动 (无检查)
:: 适用于已配置好环境的用户
:: ============================================

set PORT=5002
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo.
echo ╔════════════════════════════╗
echo ║ 抖音陪玩Agent - 快速启动   ║
echo ╠════════════════════════════╣
echo ║ http://localhost:%PORT%     ║
echo ╚════════════════════════════╝
echo.

cd /d "%~dp0"
python web\server.py --port %PORT%

pause
