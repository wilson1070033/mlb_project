#!/usr/bin/env python
"""
MLB 統計查詢系統 - 自動設置腳本 (Python版本)

這個腳本會自動執行專案設置的所有必要步驟。
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(command, description, exit_on_error=True):
    """執行命令並處理錯誤"""
    print(f"\n🔄 {description}...")
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description}完成")
        if result.stdout.strip():
            print(f"   輸出: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description}失敗")
        print(f"   錯誤: {e.stderr.strip()}")
        if exit_on_error:
            print("設置中斷")
            sys.exit(1)
        return False

def check_environment():
    """檢查環境是否正確"""
    print("🔍 檢查環境...")
    
    # 檢查是否在正確的目錄
    if not Path("manage.py").exists():
        print("❌ 錯誤：請在專案根目錄運行此腳本！")
        sys.exit(1)
    
    # 檢查Python版本
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print("❌ 錯誤：需要Python 3.8或更高版本！")
        sys.exit(1)
    
    print(f"✅ Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")

def setup_virtual_environment():
    """設置虛擬環境"""
    venv_path = Path(".venv")
    
    if venv_path.exists():
        print("✅ 虛擬環境已存在")
        
        # 在Windows上檢查虛擬環境
        if os.name == 'nt':
            activate_script = venv_path / "Scripts" / "activate.bat"
        else:
            activate_script = venv_path / "bin" / "activate"
        
        if not activate_script.exists():
            print("⚠️  虛擬環境可能損壞，建議重新建立")
    else:
        print("🔧 建立虛擬環境...")
        run_command("python -m venv .venv", "建立虛擬環境")

def install_dependencies():
    """安裝依賴套件"""
    if Path("requirements.txt").exists():
        # 根據作業系統選擇pip路徑
        if os.name == 'nt':
            pip_cmd = ".venv\\Scripts\\pip"
        else:
            pip_cmd = ".venv/bin/pip"
        
        run_command(f"{pip_cmd} install -r requirements.txt", "安裝依賴套件")
    else:
        print("⚠️  未找到requirements.txt檔案")

def setup_database():
    """設置資料庫"""
    # 根據作業系統選擇python路徑
    if os.name == 'nt':
        python_cmd = ".venv\\Scripts\\python"
    else:
        python_cmd = ".venv/bin/python"
    
    run_command(f"{python_cmd} manage.py makemigrations", "建立資料庫遷移")
    run_command(f"{python_cmd} manage.py migrate", "執行資料庫遷移")

def collect_static_files():
    """收集靜態檔案"""
    if os.name == 'nt':
        python_cmd = ".venv\\Scripts\\python"
    else:
        python_cmd = ".venv/bin/python"
    
    run_command(f"{python_cmd} manage.py collectstatic --noinput", "收集靜態檔案")

def check_django_setup():
    """檢查Django設定"""
    if os.name == 'nt':
        python_cmd = ".venv\\Scripts\\python"
    else:
        python_cmd = ".venv/bin/python"
    
    run_command(f"{python_cmd} manage.py check", "檢查Django設定")

def create_superuser():
    """建立管理員帳戶"""
    response = input("\n🤔 是否建立管理員帳戶？(y/n): ").lower()
    if response == 'y':
        if os.name == 'nt':
            python_cmd = ".venv\\Scripts\\python"
        else:
            python_cmd = ".venv/bin/python"
        
        print("\n請輸入管理員資訊：")
        os.system(f"{python_cmd} manage.py createsuperuser")

def start_server():
    """啟動開發伺服器"""
    response = input("\n🚀 是否現在啟動開發伺服器？(y/n): ").lower()
    if response == 'y':
        if os.name == 'nt':
            python_cmd = ".venv\\Scripts\\python"
        else:
            python_cmd = ".venv/bin/python"
        
        print("\n🌐 正在啟動開發伺服器...")
        print("🔗 請訪問 http://127.0.0.1:8000 查看網站")
        print("⏹️  按 Ctrl+C 停止伺服器")
        print()
        
        try:
            os.system(f"{python_cmd} manage.py runserver")
        except KeyboardInterrupt:
            print("\n👋 伺服器已停止")

def main():
    """主函數"""
    print("=" * 50)
    print("🏀 MLB 統計查詢系統 - 自動設置腳本")
    print("=" * 50)
    
    try:
        check_environment()
        setup_virtual_environment()
        install_dependencies()
        setup_database()
        collect_static_files()
        check_django_setup()
        
        print("\n" + "=" * 50)
        print("🎉 設置完成！")
        print("=" * 50)
        print("\n📋 下一步：")
        print("1. 建立管理員帳戶（可選）")
        print("2. 啟動開發伺服器")
        print("3. 訪問 http://127.0.0.1:8000 查看網站")
        
        create_superuser()
        start_server()
        
        print("\n✨ 專案已準備就緒！")
        
    except KeyboardInterrupt:
        print("\n\n👋 設置已取消")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 設置過程中發生錯誤: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
