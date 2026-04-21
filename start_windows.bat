@echo off
chcp 65001 > nul
title 抖音数据看板启动器

echo ======================================================
echo    欢迎使用抖音多维度数据抓取与分析看板系统
echo ======================================================
echo.

:: 1. 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python 3，请前往 https://www.python.org/ 下载并安装。
    echo 请确保在安装时勾选了 "Add Python to PATH"。
    pause
    exit /b
)

:: 2. 创建并激活虚拟环境
if not exist "venv" (
    echo [*] 正在创建虚拟环境 (venv)...
    python -m venv venv
)

echo [*] 正在激活虚拟环境...
call venv\Scripts\activate

:: 3. 安装依赖
echo [*] 正在检查/安装依赖包 (可能需要 1-2 分钟)...
python -m pip install --upgrade pip > nul
pip install -r requirements.txt

:: 4. 安装 Playwright 浏览器
echo [*] 正在确保浏览器内核已安装...
playwright install chromium

:: 5. 启动服务
echo.
echo [!] 即将启动后端服务...
echo [!] 请保持此窗口开启，不要关闭。
echo.

:: 在新窗口启动后端，以免阻塞当前脚本打开浏览器
start "抖音看板后端" /B python -m backend.main

:: 6. 等待并打开页面
echo [*] 等待服务器就绪 (3s)...
timeout /t 3 /nobreak > nul

echo [*] 自动打开看板页面...
start http://localhost:8000

echo.
echo ======================================================
echo    服务已启动！
echo    本地访问地址: http://localhost:8000
echo    若要停止服务，请按 Ctrl+C 或直接关闭此窗口。
echo ======================================================
echo.

:: 保持窗口不退出，以便查看后端日志
pause
