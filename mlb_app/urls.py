"""
MLB 應用程式的 URL 配置

這個檔案定義了 mlb_app 應用程式的所有 URL 路由。
它就像是應用程式的導航地圖，告訴 Django 如何將不同的網址對應到相應的視圖函數。

URL 設計原則：
1. 簡潔明瞭：URL 應該容易理解和記憶
2. RESTful 風格：遵循 REST API 的設計慣例
3. 語義化：URL 本身就能說明它的功能
4. 一致性：相似功能使用相似的 URL 結構

例如：
- /players/search/ 用於搜尋球員
- /players/123/ 用於查看 ID 為 123 的球員詳細資訊
- /players/123/stats/ 用於查看該球員的統計數據
- /games/2024-04-09/ 用於查看特定日期的比賽

這種設計讓使用者和開發者都能直觀地理解每個 URL 的功能。
"""

from django.urls import path
from . import views
from . import ai_views  # 導入 AI 功能視圖
from django.contrib.auth import views as auth_views # For Login/Logout

# 應用程式的命名空間
# 這讓我們可以在模板和其他地方使用 'mlb_app:view_name' 的方式引用 URL
# 避免與其他應用程式的 URL 名稱衝突
app_name = 'mlb_app'

urlpatterns = [
    # 首頁
    # URL: /
    # 功能: 顯示首頁，包含今日比賽和熱門球員
    path('', views.index, name='index'),
    
    # 比賽相關的 URL
    # URL: /games/
    # 功能: 查詢特定日期的比賽，日期通過 GET 參數傳遞
    # 例如: /games/?date=2024-04-09
    path('games/', views.games_by_date, name='games'),
    
    # 球員搜尋
    # URL: /players/search/
    # 功能: 球員搜尋頁面，支援關鍵字搜尋
    # 例如: /players/search/?q=Shohei+Ohtani
    path('players/search/', views.search_players, name='search_players'),
    
    # 球員詳細資訊
    # URL: /players/123/
    # 功能: 顯示特定球員的詳細資訊
    # 例如: /players/660271/ （大谷翔平的 MLB ID）
    path('players/<int:player_id>/', views.player_detail, name='player_detail'),
    
    # 球員統計數據
    # URL: /players/123/stats/
    # 功能: 顯示球員的詳細統計數據，支援不同的查詢參數
    # 例如: /players/660271/stats/?stat_group=hitting&stat_type=season&season=2024
    path('players/<int:player_id>/stats/', views.player_stats, name='player_stats'),

    # 使用者註冊
    # URL: /register/
    # 功能: 顯示註冊表單並處理註冊請求
    path('register/', views.register_request, name='register'),

    # 使用者登入/登出
    path('login/', auth_views.LoginView.as_view(template_name='mlb_app/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'), # Redirect to home page after logout
    
    # AI 功能相關 URL
    # 
    # AI 球員推薦
    # URL: /players/123/ai-recommendations/
    # 功能: 使用機器學習演算法為指定球員推薦相似球員
    # 例如: /players/660271/ai-recommendations/
    path('players/<int:player_id>/ai-recommendations/', ai_views.ai_player_recommendations, name='ai_recommendations'),
    
    # AI 表現預測
    # URL: /players/123/prediction/
    # 功能: 使用預測模型預測球員未來表現
    # 例如: /players/660271/prediction/
    path('players/<int:player_id>/prediction/', ai_views.ai_performance_prediction, name='ai_prediction'),
    
    # 使用者個人化儀表板
    # URL: /dashboard/
    # 功能: 顯示個人化的使用者儀表板，需要登入
    path('dashboard/', ai_views.user_dashboard, name='user_dashboard'),
    
    # API 端點 - 這些 URL 返回 JSON 數據，供前端 JavaScript 使用
    # 
    # 比賽資訊 API
    # URL: /api/games/
    # 功能: 返回 JSON 格式的比賽資訊
    # 用途: 供前端 AJAX 請求使用，實現動態更新
    path('api/games/', views.api_games_json, name='api_games'),
    
    # 球員搜尋 API
    # URL: /api/players/search/
    # 功能: 返回 JSON 格式的球員搜尋結果
    # 用途: 供自動完成功能使用
    path('api/players/search/', views.api_player_search_json, name='api_player_search'),
    
    # AI 洞察 API
    # URL: /api/ai-insights/
    # 功能: 返回 AI 分析結果，支援多種洞察類型
    # 用途: 供前端 JavaScript 動態加載数據使用
    # 例如: /api/ai-insights/?type=trends
    path('api/ai-insights/', ai_views.ai_insights_api, name='api_ai_insights'),
    
    # 靜態頁面
    # 
    # 關於頁面
    # URL: /about/
    # 功能: 顯示應用程式的介紹和開發資訊
    path('about/', views.about, name='about'),
    
    # 幫助頁面
    # URL: /help/
    # 功能: 顯示使用說明和常見問題
    path('help/', views.help_page, name='help'),

    # 球隊列表
    # URL: /teams/
    # 功能: 顯示所有球隊的列表
    path('teams/', views.teams_list, name='teams_list'),

    # 球隊詳細資訊
    # URL: /teams/123/
    # 功能: 顯示特定球隊的詳細資訊 (123 為 team_id, 即 mlb_id)
    path('teams/<int:team_id>/', views.team_detail, name='team_detail'),

    # 球隊球員名單
    # URL: /teams/123/roster/
    # 功能: 顯示特定球隊的球員名單
    path('teams/<int:team_id>/roster/', views.team_roster, name='team_roster'),
]

# URL 設計說明：
#
# 1. 首頁 (/)
#    - 這是使用者首次訪問網站看到的頁面
#    - 提供網站的主要功能導航
#    - 顯示今日比賽和熱門球員
#
# 2. 比賽查詢 (/games/)
#    - 使用 GET 參數傳遞日期，保持 URL 簡潔
#    - 支援直接在 URL 中指定日期進行查詢
#    - 例如: /games/?date=2024-04-09
#
# 3. 球員相關 URL (/players/...)
#    - 使用階層式結構組織球員相關功能
#    - /players/search/ 用於搜尋
#    - /players/<id>/ 用於查看詳細資訊
#    - /players/<id>/stats/ 用於查看統計數據
#
# 4. API 端點 (/api/...)
#    - 專門的 API 路徑，返回 JSON 數據
#    - 支援前端 JavaScript 的 AJAX 請求
#    - 可以獨立快取和優化
#
# 5. 靜態頁面
#    - 簡單的資訊頁面
#    - 提供網站的輔助資訊

# 未來可能的擴展 URL：
#
# 如果要添加更多功能，可以考慮以下 URL 結構：
#
# # 球隊相關
# path('teams/', views.teams_list, name='teams_list'),
# path('teams/<int:team_id>/', views.team_detail, name='team_detail'),
# path('teams/<int:team_id>/roster/', views.team_roster, name='team_roster'),
#
# # 統計排行榜
# path('stats/leaders/', views.stat_leaders, name='stat_leaders'),
# path('stats/leaders/<str:stat_type>/', views.stat_leaders_detail, name='stat_leaders_detail'),
#
# # 賽程表
# path('schedule/', views.schedule, name='schedule'),
# path('schedule/<int:year>/<int:month>/', views.monthly_schedule, name='monthly_schedule'),
#
# # 用戶功能（如果添加用戶系統）
# path('favorites/', views.user_favorites, name='user_favorites'),
# path('favorites/add/<int:player_id>/', views.add_favorite, name='add_favorite'),
#
# # 數據分析
# path('analytics/', views.analytics_dashboard, name='analytics'),
# path('analytics/team-comparison/', views.team_comparison, name='team_comparison'),

# URL 命名慣例：
#
# 1. 使用小寫字母和底線
# 2. 名稱應該描述功能，而不是實現細節
# 3. 保持一致的命名模式
# 4. API 端點通常以 'api_' 開頭
# 5. 詳細頁面通常以 '_detail' 結尾
# 6. 列表頁面可以省略 '_list' 後綴（如果語義清楚）

# 這種 URL 設計的優點：
#
# 1. 可讀性：任何人都能從 URL 理解頁面的功能
# 2. 可預測性：使用者可以猜測相關頁面的 URL
# 3. SEO 友好：搜索引擎喜歡語義化的 URL
# 4. 維護性：清晰的結構讓程式碼更容易維護
# 5. 擴展性：容易添加新的功能而不破壞現有結構
