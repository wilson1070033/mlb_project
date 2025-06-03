"""
ASGI config for mlb_project project.

ASGI（Asynchronous Server Gateway Interface）是 WSGI 的現代化進化版本。
如果說 WSGI 是一位傳統的翻譯員，那麼 ASGI 就是一位現代化的多語言翻譯員，
不僅能處理傳統的 HTTP 請求，還能處理 WebSocket 連接、長時間運行的連接等現代 Web 功能。

ASGI 的主要優勢在於它的非同步特性：
- 傳統的 WSGI 就像一個單線道的橋樑，一次只能讓一輛車通過
- ASGI 則像是一座多線道的現代化橋樑，可以同時處理多個請求

對於我們的 MLB 統計應用程式來說，雖然目前主要使用同步處理，
但這個配置讓我們為未來可能的功能擴展做好準備，
例如實時比分更新、即時聊天功能等。

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

# 設定 Django 設定模組的環境變數
# 這與 WSGI 配置相同，告訴 ASGI 應用程式在哪裡找到專案設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mlb_project.settings')

# 建立 ASGI 應用程式物件
# 這個物件能夠處理各種類型的連接：HTTP、WebSocket 等
application = get_asgi_application()

# 未來如果您想要添加 WebSocket 功能（例如實時比分更新），
# 可以在這裡添加相應的路由配置：
#
# from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.auth import AuthMiddlewareStack
# import mlb_app.routing
#
# application = ProtocolTypeRouter({
#     "http": get_asgi_application(),
#     "websocket": AuthMiddlewareStack(
#         URLRouter(
#             mlb_app.routing.websocket_urlpatterns
#         )
#     ),
# })
#
# 這樣的配置讓您的應用程式既能處理傳統的 HTTP 請求，
# 也能處理實時的 WebSocket 連接
