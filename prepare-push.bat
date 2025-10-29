@echo off
echo 🚀 Подготовка к пушу в GitHub репозиторий
echo.

REM Проверка Git
git --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Git не установлен! Установите Git с https://git-scm.com
    pause
    exit /b 1
)

REM Добавление всех файлов
echo 📁 Добавление файлов в Git...
git add .

REM Проверка статуса
echo 📊 Статус репозитория:
git status

echo.
echo ✅ Готово к коммиту!
echo.
echo 📝 Для завершения выполните:
echo    git commit -m "Initial commit: Executor Balancer with Dashboard"
echo    git push origin main
echo.
pause
