@echo off
echo ====================================
echo AR健身教练 Web应用启动脚本
echo ====================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python
    pause
    exit /b 1
)

echo 正在检查依赖...
pip show Flask >nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo 依赖安装失败，请检查网络连接
        pause
        exit /b 1
    )
)

echo.
echo 正在启动Web应用...
echo 应用将在 http://localhost:5000 启动
echo 按 Ctrl+C 停止服务器
echo.

python app.py

pause

