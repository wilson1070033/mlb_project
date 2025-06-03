"""
WSGI config for mlb_project project.

WSGI（Web Server Gateway Interface）是 Python Web 應用程式的標準介面規範。
它就像是一個翻譯員，讓您的 Django 應用程式能夠與各種不同的 Web 伺服器
（如 Apache、Nginx、Gunicorn 等）進行有效的溝通。

想像一下，如果 Django 是一位只會說中文的專家，而 Web 伺服器是只會說英文的接待員，
那麼 WSGI 就是這兩者之間的翻譯員，確保他們能夠正確地傳遞訊息。

這個檔案在開發階段可能不太明顯，但在部署到正式環境時就變得非常重要。
當您準備將應用程式部署到伺服器上時，WSGI 就是讓您的應用程式能夠在真實環境中運行的關鍵。

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# 設定 Django 設定模組的環境變數
# 這告訴 WSGI 應用程式在哪裡可以找到 Django 專案的設定檔
# 就像給翻譯員一本字典，讓他知道如何正確地翻譯不同的詞彙
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mlb_project.settings')

# 建立 WSGI 應用程式物件
# 這個物件是 Web 伺服器和 Django 應用程式之間的橋樑
# get_wsgi_application() 函數會根據設定檔建立一個符合 WSGI 標準的應用程式物件
application = get_wsgi_application()

# 在正式部署環境中，您的 Web 伺服器配置會指向這個 application 物件
# 例如在 Gunicorn 中，您可能會使用這樣的命令：
# gunicorn mlb_project.wsgi:application
#
# 這告訴 Gunicorn：「請使用 mlb_project.wsgi 模組中的 application 物件來處理所有的 Web 請求」
