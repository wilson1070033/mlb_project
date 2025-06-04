@echo off
echo ================================================
echo MLB 統計查詢系統 - 自動設置腳本
echo ================================================
echo.

REM 檢查是否在正確的目錄
if not exist "manage.py" (
    echo 錯誤：請在專案根目錄運行此腳本！
    pause
    exit /b 1
)

echo 步驟 1: 啟動虛擬環境...
call .venv\Scripts\activate
if %errorlevel% neq 0 (
    echo 警告：虛擬環境啟動失敗，繼續使用系統Python...
)

echo.
echo 步驟 2: 檢查Django版本...
python -c "import django; print('Django版本:', django.get_version())"

echo.
echo 步驟 3: 安裝/更新依賴套件...
pip install -r requirements.txt

echo.
echo 步驟 4: 建立資料庫遷移...
python manage.py makemigrations
if %errorlevel% neq 0 (
    echo 錯誤：資料庫遷移檔案建立失敗！
    pause
    exit /b 1
)

echo.
echo 步驟 5: 執行資料庫遷移...
python manage.py migrate
if %errorlevel% neq 0 (
    echo 錯誤：資料庫遷移執行失敗！
    pause
    exit /b 1
)

echo.
echo 步驟 6: 收集靜態檔案...
python manage.py collectstatic --noinput

echo.
echo 步驟 7: 檢查Django設定...
python manage.py check

echo.
echo ================================================
echo 設置完成！
echo ================================================
echo.
echo 下一步：
echo 1. 建立管理員帳戶：python manage.py createsuperuser
echo 2. 啟動伺服器：python manage.py runserver
echo 3. 訪問 http://127.0.0.1:8000 查看網站
echo.

set /p create_admin="是否現在建立管理員帳戶？(y/n): "
if /i "%create_admin%"=="y" (
    echo.
    echo 請輸入管理員資訊：
    python manage.py createsuperuser
)

echo.
set /p start_server="是否現在啟動開發伺服器？(y/n): "
if /i "%start_server%"=="y" (
    echo.
    echo 正在啟動開發伺服器...
    echo 請訪問 http://127.0.0.1:8000 查看網站
    echo 按 Ctrl+C 停止伺服器
    echo.
    python manage.py runserver
)

echo.
echo 設置完成！專案已準備就緒。
pause
