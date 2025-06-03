"""
Django 管理後台配置

這個檔案配置了 Django 管理後台的介面，讓我們可以通過網頁介面管理資料庫中的資料。
Django 管理後台就像是一個專業的資料庫管理工具，但是以網頁的形式呈現，
讓我們可以輕鬆地：

1. 查看和搜尋資料
2. 新增、編輯、刪除記錄
3. 批量操作資料
4. 匯入和匯出資料
5. 管理用戶權限

這對於網站管理者來說是一個非常有用的工具，特別是在開發和維護階段。

管理後台的設計原則：
- 使用者友好：介面應該直觀易用
- 功能完整：提供所有必要的資料操作功能
- 安全可靠：適當的權限控制和資料驗證
- 效能優化：避免不必要的資料庫查詢
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Team, Player, GameLog, SearchHistory


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    """
    球隊管理介面配置
    
    這個類別定義了球隊模型在管理後台中的顯示和操作方式。
    我們可以自定義列表顯示、搜尋、過濾、編輯等各個方面。
    """
    
    # 列表頁面顯示的欄位
    # 這些欄位會在球隊列表中顯示，讓管理者能快速瀏覽球隊資訊
    list_display = [
        'name',           # 球隊名稱
        'abbreviation',   # 縮寫
        'city',          # 城市
        'league',        # 聯盟
        'division',      # 分區
        'mlb_id',        # MLB ID
        'created_at',    # 建立時間
    ]
    
    # 可點擊進入詳細頁面的欄位
    # 點擊這些欄位可以進入球隊的編輯頁面
    list_display_links = ['name', 'abbreviation']
    
    # 可搜尋的欄位
    # 管理者可以在這些欄位中進行關鍵字搜尋
    search_fields = [
        'name',           # 球隊名稱
        'abbreviation',   # 縮寫
        'city',          # 城市
        'mlb_id',        # MLB ID
    ]
    
    # 側邊欄過濾器
    # 這些過濾器讓管理者可以快速篩選特定條件的球隊
    list_filter = [
        'league',        # 按聯盟過濾
        'division',      # 按分區過濾
        'created_at',    # 按建立時間過濾
    ]
    
    # 只讀欄位
    # 這些欄位在編輯時不能修改，通常是系統自動生成的
    readonly_fields = ['created_at', 'updated_at']
    
    # 每頁顯示的記錄數
    list_per_page = 25
    
    # 編輯頁面的欄位分組
    # 這讓編輯介面更加組織化和易用
    fieldsets = (
        ('基本資訊', {
            'fields': ('name', 'abbreviation', 'city')
        }),
        ('聯盟資訊', {
            'fields': ('league', 'division')
        }),
        ('系統資訊', {
            'fields': ('mlb_id', 'created_at', 'updated_at'),
            'classes': ('collapse',),  # 預設摺疊這個區塊
        }),
    )
    
    # 排序方式
    ordering = ['name']
    
    def get_queryset(self, request):
        """
        自定義查詢集
        
        這個方法讓我們可以優化資料庫查詢，提高管理後台的性能。
        """
        return super().get_queryset(request)


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    """
    球員管理介面配置
    
    球員是我們系統中最重要的實體之一，因此需要一個功能豐富的管理介面。
    """
    
    # 列表頁面顯示的欄位
    list_display = [
        'full_name',           # 球員姓名
        'current_team_display', # 目前球隊（自定義顯示）
        'primary_position',    # 主要位置
        'height_cm',          # 身高
        'weight_kg',          # 體重
        'birth_date',         # 出生日期
        'photo_preview',      # 照片預覽（自定義）
        'mlb_id',            # MLB ID
    ]
    
    list_display_links = ['full_name']
    
    # 搜尋欄位
    search_fields = [
        'full_name',     # 球員姓名
        'mlb_id',       # MLB ID
        'current_team__name',  # 球隊名稱（關聯欄位）
        'current_team__abbreviation',  # 球隊縮寫
    ]
    
    # 過濾器
    list_filter = [
        'primary_position',    # 位置
        'current_team',       # 球隊
        'bat_hand',          # 慣用手
        'created_at',        # 建立時間
    ]
    
    # 只讀欄位
    readonly_fields = ['created_at', 'updated_at', 'photo_preview']
    
    # 每頁顯示數量
    list_per_page = 20
    
    # 欄位分組
    fieldsets = (
        ('基本資訊', {
            'fields': ('full_name', 'mlb_id', 'current_team', 'primary_position')
        }),
        ('身體資訊', {
            'fields': ('birth_date', 'height_cm', 'weight_kg', 'bat_hand')
        }),
        ('照片', {
            'fields': ('photo', 'photo_preview'),
            'classes': ('collapse',),
        }),
        ('系統資訊', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    # 排序
    ordering = ['full_name']
    
    # 原始ID欄位，用於快速查找
    raw_id_fields = ['current_team']
    
    def current_team_display(self, obj):
        """
        自定義球隊顯示方法
        
        這個方法讓我們可以在列表中更好地顯示球隊資訊。
        如果球員沒有球隊，顯示「自由球員」。
        """
        if obj.current_team:
            return f"{obj.current_team.name} ({obj.current_team.abbreviation})"
        return "自由球員"
    
    current_team_display.short_description = "目前球隊"
    current_team_display.admin_order_field = 'current_team__name'
    
    def photo_preview(self, obj):
        """
        照片預覽方法
        
        在管理後台中顯示球員照片的縮圖。
        """
        if obj.photo:
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius: 50%;" />',
                obj.photo.url
            )
        return "無照片"
    
    photo_preview.short_description = "照片預覽"


@admin.register(GameLog)
class GameLogAdmin(admin.ModelAdmin):
    """
    比賽記錄管理介面配置
    
    比賽記錄包含了大量的統計數據，需要一個清晰的管理介面。
    """
    
    # 列表顯示
    list_display = [
        'player',           # 球員
        'game_date',        # 比賽日期
        'opponent_team',    # 對手
        'is_home',         # 是否主場
        'batting_avg_display',  # 打擊率（計算欄位）
        'hits',            # 安打
        'at_bats',         # 打數
        'runs',            # 得分
        'rbi',             # 打點
        'home_runs',       # 全壘打
    ]
    
    list_display_links = ['player', 'game_date']
    
    # 搜尋
    search_fields = [
        'player__full_name',        # 球員姓名
        'opponent_team__name',      # 對手球隊名稱
        'opponent_team__abbreviation',  # 對手球隊縮寫
    ]
    
    # 過濾器
    list_filter = [
        'game_date',        # 比賽日期
        'is_home',         # 主客場
        'opponent_team',   # 對手球隊
        'player__current_team',  # 球員球隊
        'created_at',      # 建立時間
    ]
    
    # 只讀欄位
    readonly_fields = ['created_at', 'batting_avg_display']
    
    # 每頁顯示數量
    list_per_page = 50
    
    # 日期層次結構導航
    date_hierarchy = 'game_date'
    
    # 欄位分組
    fieldsets = (
        ('比賽資訊', {
            'fields': ('player', 'game_date', 'opponent_team', 'is_home')
        }),
        ('打擊統計', {
            'fields': ('at_bats', 'hits', 'runs', 'rbi', 'home_runs', 'batting_avg_display')
        }),
        ('投球統計', {
            'fields': ('innings_pitched', 'strikeouts', 'walks', 'earned_runs'),
            'classes': ('collapse',),
        }),
        ('系統資訊', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )
    
    # 排序
    ordering = ['-game_date', 'player__full_name']
    
    # 原始ID欄位
    raw_id_fields = ['player', 'opponent_team']
    
    def batting_avg_display(self, obj):
        """
        顯示打擊率
        
        計算並顯示該場比賽的打擊率。
        """
        return f"{obj.batting_average:.3f}"
    
    batting_avg_display.short_description = "打擊率"
    batting_avg_display.admin_order_field = 'hits'


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    """
    搜尋歷史管理介面配置
    
    搜尋歷史幫助我們了解使用者的使用模式和熱門內容。
    """
    
    # 列表顯示
    list_display = [
        'search_type',      # 搜尋類型
        'search_query',     # 搜尋關鍵字
        'results_count',    # 結果數量
        'search_time',      # 搜尋時間
        'ip_address',       # IP 地址
    ]
    
    list_display_links = ['search_query']
    
    # 搜尋
    search_fields = [
        'search_query',     # 搜尋關鍵字
        'ip_address',       # IP 地址
    ]
    
    # 過濾器
    list_filter = [
        'search_type',      # 搜尋類型
        'search_time',      # 搜尋時間
        'results_count',    # 結果數量
    ]
    
    # 只讀欄位（搜尋歷史不應該被修改）
    readonly_fields = [
        'search_type', 'search_query', 'results_count', 
        'search_time', 'ip_address'
    ]
    
    # 每頁顯示數量
    list_per_page = 100
    
    # 日期層次結構
    date_hierarchy = 'search_time'
    
    # 排序
    ordering = ['-search_time']
    
    # 禁用添加和修改功能（這是歷史記錄，只能查看）
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        # 只允許批量刪除舊記錄
        return request.user.is_superuser


# 自定義管理後台的標題和描述
admin.site.site_header = "MLB 統計查詢系統 - 管理後台"
admin.site.site_title = "MLB 統計管理"
admin.site.index_title = "歡迎使用 MLB 統計查詢系統管理後台"

# 自定義管理後台的操作
class ExportCsvMixin:
    """
    CSV 匯出混合類別
    
    這個混合類別為管理後台添加 CSV 匯出功能。
    管理者可以選擇記錄並匯出為 CSV 檔案。
    """
    
    def export_as_csv(self, request, queryset):
        """
        匯出選中的記錄為 CSV 檔案
        """
        import csv
        from django.http import HttpResponse
        
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={meta}.csv'
        
        writer = csv.writer(response)
        writer.writerow(field_names)
        
        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in field_names])
        
        return response
    
    export_as_csv.short_description = "匯出選中的記錄為 CSV"

# 為需要匯出功能的模型添加這個混合類別
# 可以在各個 Admin 類別中添加：actions = ['export_as_csv']

# 管理後台的進階功能說明：
#
# 1. 自定義動作（Actions）
#    - 可以添加批量操作功能
#    - 例如批量更新、批量刪除、匯出等
#
# 2. 內聯編輯（Inline）
#    - 在一個頁面中編輯相關的模型
#    - 例如在球員頁面中直接編輯比賽記錄
#
# 3. 自定義欄位顯示
#    - 格式化日期、數字
#    - 添加圖片預覽
#    - 建立連結到相關頁面
#
# 4. 權限控制
#    - 控制不同使用者的訪問權限
#    - 限制特定操作的使用者
#
# 5. 效能優化
#    - 使用 select_related 和 prefetch_related
#    - 添加資料庫索引
#    - 限制查詢數量

# 使用管理後台的注意事項：
#
# 1. 安全性
#    - 管理後台應該只對授權使用者開放
#    - 使用強密碼和雙因子認證
#    - 定期檢查使用者權限
#
# 2. 備份
#    - 在進行大量資料操作前先備份
#    - 測試環境中驗證操作結果
#
# 3. 監控
#    - 記錄重要的管理操作
#    - 監控異常的資料變更
