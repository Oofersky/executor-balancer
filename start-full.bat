@echo off
echo 🚀 Executor Balancer - Полный запуск с Dashboard
echo.

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не установлен! Установите Python 3.8+ с https://python.org
    pause
    exit /b 1
)

REM Установка полных зависимостей
echo 📦 Установка полных зависимостей...
pip install -r requirements-full.txt

REM Запуск приложения
echo ▶️ Запуск приложения на http://localhost:8006
echo.
echo 🌐 Доступные страницы:
echo    http://localhost:8006 - Главная страница
echo    http://localhost:8006/app - Приложение
echo    http://localhost:8006/dashboard - Дашборд с метриками
echo    http://localhost:8006/docs - API документация
echo.
echo 📊 Dashboard включает:
echo    - Метрики исполнителей
echo    - Статистика заявок
echo    - Графики производительности
echo    - WebSocket обновления в реальном времени
echo.
echo ⏹️ Для остановки нажмите Ctrl+C
echo.

python -m app.main
