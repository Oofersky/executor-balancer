@echo off
cd /d "%~dp0"
echo 🚀 Executor Balancer - Быстрый запуск
echo.
echo 📦 Устанавливаем зависимости...
pip install fastapi uvicorn pydantic pydantic-settings jinja2 python-multipart
echo.
echo ▶️ Запускаем приложение...
echo 🌐 Откройте: http://localhost:8006
echo.
python -m app.main
