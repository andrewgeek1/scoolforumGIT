@echo off
echo ========================================
echo    Школьная социальная сеть
echo    Домен: testingfm.ru
echo    IP: 178.212.250.85
echo ========================================
echo.

cd /d "%~dp0\.."

echo [1/3] Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo Ошибка: Python не установлен!
    pause
    exit /b 1
)

echo [2/3] Установка зависимостей...
pip install -r requirements.txt

echo [3/3] Запуск сервера...
echo.
echo Сервер будет доступен по адресам:
echo   - http://testingfm.ru:5000
echo   - http://178.212.250.85:5000
echo   - http://localhost:5000
echo.
echo Нажмите Ctrl+C для остановки
echo.

python app.py --port 5000 --host 0.0.0.0

pause