"""
Django 應用程式配置檔案

這個檔案定義了 mlb_app 應用程式的配置資訊，就像是應用程式的身分證。
Django 使用這個配置來正確地載入和管理應用程式的各種功能。

應用程式配置的概念就像是告訴 Django：
「這是 mlb_app 應用程式，它的名稱是什麼，有什麼特殊設定」

透過這個配置，我們可以控制應用程式的行為，例如自動發現模型、
設定信號處理器、或者定義應用程式啟動時需要執行的初始化程式碼。
"""

from django.apps import AppConfig


class MlbAppConfig(AppConfig):
    """
    MLB 應用程式的配置類別
    
    這個類別繼承自 Django 的 AppConfig，它定義了應用程式的基本資訊和行為。
    每個 Django 應用程式都需要有一個這樣的配置類別。
    """
    
    # 預設的自動增量欄位類型
    # 這決定了當我們建立模型時，主鍵欄位應該使用什麼類型
    # BigAutoField 可以處理更大的數字範圍，適合現代應用程式的需求
    default_auto_field = 'django.db.models.BigAutoField'
    
    # 應用程式的完整名稱
    # 這個名稱必須與 settings.py 中 INSTALLED_APPS 列表中的名稱一致
    name = 'mlb_app'
    
    # 應用程式的可讀性名稱（可選）
    # 這個名稱會在 Django 管理介面中顯示，讓使用者更容易理解
    verbose_name = 'MLB 統計查詢應用程式'
    
    def ready(self):
        """
        應用程式準備完成時的回調函數
        
        這個方法會在 Django 完全載入應用程式後被呼叫。
        您可以在這裡放置應用程式啟動時需要執行的初始化程式碼，
        例如：
        - 註冊信號處理器
        - 設定快取
        - 初始化第三方服務
        - 載入配置資料
        
        對於我們的 MLB 應用程式，這裡可能會用來：
        - 檢查 MLB API 的連接狀態
        - 初始化資料快取
        - 載入球隊和球員的基本資訊
        """
        # 目前我們不需要特殊的初始化程式碼
        # 但這個方法為未來的擴展提供了便利
        pass
        
        # 未來您可能會在這裡添加類似這樣的程式碼：
        # try:
        #     from . import signals  # 載入信號處理器
        #     from .utils import mlb_api  # 初始化 API 連接
        #     logger.info("MLB 應用程式初始化完成")
        # except Exception as e:
        #     logger.error(f"MLB 應用程式初始化失敗: {e}")
