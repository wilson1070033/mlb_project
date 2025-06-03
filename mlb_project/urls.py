"""
URL configuration for mlb_project project.

這是整個 Django 專案的主要 URL 配置檔案，它就像是一個網站的導航地圖。
當使用者在瀏覽器中輸入不同的網址時，Django 會根據這裡的配置決定要執行哪個功能。

URL 模式的工作原理就像是郵遞系統：
1. 使用者輸入網址（就像寫地址）
2. Django 查看這個檔案中的 URL 模式（就像郵務員查看地址簿）
3. 找到匹配的模式後，將請求轉發到對應的視圖（就像將信件送到正確地址）

這種設計讓我們能夠建立清晰、有組織的網站結構，同時保持程式碼的模組化。

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

# 主專案的 URL 模式配置
# 這個列表定義了所有可能的 URL 路徑和它們對應的處理方式
urlpatterns = [
    # Django 管理後台的 URL
    # 這是 Django 內建的管理介面，讓您可以管理資料庫中的資料
    # 在開發階段，您可以通過 http://localhost:8000/admin/ 訪問
    path('admin/', admin.site.urls),
    
    # 包含我們 MLB 應用程式的所有 URL
    # 這行代碼告訴 Django：「當網址以 '/' 開始時，請查看 mlb_app.urls 檔案中的配置」
    # include() 函數讓我們可以將不同應用程式的 URL 配置分開管理，這樣程式碼更加組織化
    path('', include('mlb_app.urls')),
    
    # 您可以在這裡添加其他應用程式的 URL 配置
    # 例如：path('api/', include('api.urls')) 用於 API 端點
    # 或者：path('users/', include('users.urls')) 用於用戶管理功能
]

# 在開發環境中提供媒體文件的服務
# 這個配置讓 Django 開發伺服器能夠直接提供用戶上傳的文件（例如球員照片）
# 在正式部署環境中，這些文件通常由網頁伺服器（如 Nginx 或 Apache）直接提供
if settings.DEBUG:
    # static() 函數建立一個 URL 模式，用於提供媒體文件
    # 這樣當使用者訪問 /media/player_photos/某個檔案.jpg 時
    # Django 就會從 MEDIA_ROOT 目錄中找到對應的檔案並提供給瀏覽器
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # 同樣地，在開發環境中也提供靜態文件的服務
    # 靜態文件包括 CSS、JavaScript、圖片等不會變動的資源
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# 您可以在這裡添加自定義的錯誤處理頁面
# 例如：handler404 = 'mlb_app.views.custom_404'
# 這讓您能夠為 404 錯誤、500 錯誤等提供自定義的美觀頁面

# 如果您想要根路徑直接重定向到某個特定頁面，可以使用：
# path('', lambda request: redirect('mlb_app:index'), name='home')
