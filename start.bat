@echo off
echo 🚀 Запуск Executor Balancer...
echo.

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не установлен! Установите Python 3.8+ с https://python.org
    pause
    exit /b 1
)

REM Установка зависимостей
echo 📦 Установка зависимостей...
pip install -r requirements.txt

REM Запуск приложения
echo ▶️ Запуск приложения на http://localhost:8006
echo.
echo 🌐 Откройте браузер и перейдите по адресу:
echo    http://localhost:8006 - Главная страница
echo    http://localhost:8006/app - Приложение
echo    http://localhost:8006/dashboard - Дашборд
echo.
echo ⏹️ Для остановки нажмите Ctrl+C
echo.

python -m app.main
