#!/usr/bin/env python
"""
Django's command-line utility for administrative tasks.
這是 Django 專案的管理工具，就像是專案的指揮中心。
透過這個文件，我們可以執行各種 Django 命令，例如啟動開發伺服器、
建立資料庫遷移、創建超級用戶等等。
"""
import os
import sys


def main():
    """Run administrative tasks."""
    # 設定 Django 設定模組的環境變數
    # 這告訴 Django 在哪裡可以找到專案的設定檔
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mlb_project.settings')
    try:
        # 嘗試從 Django 核心管理模組導入執行命令的函數
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        # 如果導入失敗，提供有用的錯誤訊息幫助除錯
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    
    # 執行命令列指令，sys.argv 包含了使用者輸入的參數
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
