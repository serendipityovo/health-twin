@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   康孪生 HealthTwin 启动中...
echo ============================================
if not exist .env (
    copy .env.example .env >nul
    echo [提示] 已从 .env.example 创建 .env，请按需修改模型配置
)
pip install -r requirements.txt -q
streamlit run app.py
pause
