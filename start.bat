@echo off
chcp 65001 >nul
echo ================================================
echo   股票技术分析系统 启动中...
echo ================================================
cd /d %~dp0

if not exist .env (
    echo [警告] 未找到 .env 文件，请复制 .env.example 为 .env 并填入 API Key
    echo.
)

echo 安装/检查依赖...
pip install -r requirements.txt -q

echo.
echo 启动服务器: http://localhost:8000
echo 按 Ctrl+C 停止服务
echo.
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
