"""
Django 資料模型定義

這個檔案定義了我們 MLB 統計應用程式中所有的資料模型。
模型就像是資料的藍圖，它們告訴 Django 如何在資料庫中組織和儲存資料。

每個模型類別對應資料庫中的一個表格，而模型的每個屬性則對應表格中的一個欄位。
這種對應關係讓我們能夠用 Python 程式碼來操作資料庫，而不需要直接寫 SQL 語法。

想像一下，如果資料庫是一個大型圖書館，那麼模型就是圖書館的分類系統，
告訴我們書籍應該如何分類、編號、和組織。

關於模型設計的思考：
- 每個模型都應該代表一個清楚的概念（例如：球員、球隊、比賽）
- 模型之間的關係應該反映真實世界中的關係
- 欄位的選擇應該平衡功能需求和效能考量
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse
import os


class Team(models.Model):
    """
    球隊模型
    
    這個模型儲存 MLB 球隊的基本資訊。每支球隊都有獨特的識別碼、名稱和其他相關資訊。
    這就像是球隊的身分證，記錄了球隊的基本檔案。
    """
    
    # MLB 官方球隊 ID，這個 ID 與 MLB API 中的 ID 對應
    # 使用 unique=True 確保每支球隊只有一個記錄
    mlb_id = models.IntegerField(
        unique=True, 
        verbose_name="MLB 球隊 ID",
        help_text="MLB 官方 API 中的球隊識別碼"
    )
    
    # 球隊全名，例如 "New York Yankees"
    name = models.CharField(
        max_length=100, 
        verbose_name="球隊名稱",
        help_text="球隊的完整名稱"
    )
    
    # 球隊縮寫，例如 "NYY"
    abbreviation = models.CharField(
        max_length=5, 
        verbose_name="球隊縮寫",
        help_text="球隊的縮寫代碼"
    )
    
    # 球隊所在城市
    city = models.CharField(
        max_length=50, 
        verbose_name="所在城市",
        blank=True,
        help_text="球隊所在的城市"
    )
    
    # 聯盟資訊（美國聯盟 AL 或國家聯盟 NL）
    league = models.CharField(
        max_length=50, 
        verbose_name="聯盟",
        blank=True,
        help_text="球隊所屬的聯盟"
    )
    
    # 分區資訊
    division = models.CharField(
        max_length=50, 
        verbose_name="分區",
        blank=True,
        help_text="球隊所屬的分區"
    )
    
    # 記錄建立和更新時間
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="建立時間"
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name="更新時間"
    )
    
    class Meta:
        verbose_name = "球隊"
        verbose_name_plural = "球隊"
        ordering = ['name']  # 按球隊名稱排序
    
    def __str__(self):
        """
        字串表示方法
        當我們在 Django 管理介面或其他地方顯示這個模型時，會顯示這個字串
        """
        return f"{self.name} ({self.abbreviation})"
    
    def get_absolute_url(self):
        """
        取得球隊詳細資訊頁面的 URL
        這個方法讓我們能夠輕鬆地產生指向球隊詳細頁面的連結
        """
        return reverse('mlb_app:team_detail', kwargs={'team_id': self.mlb_id})


class Player(models.Model):
    """
    球員模型
    
    這個模型儲存球員的基本資訊。每個球員都有獨特的識別碼、姓名、位置等資訊。
    想像這是球員的個人檔案，記錄了他們的基本資料。
    """
    
    # 位置選擇
    POSITION_CHOICES = [
        ('P', '投手'),
        ('C', '捕手'),
        ('1B', '一壘手'),
        ('2B', '二壘手'),
        ('3B', '三壘手'),
        ('SS', '游擊手'),
        ('LF', '左外野手'),
        ('CF', '中外野手'),
        ('RF', '右外野手'),
        ('DH', '指定打擊'),
        ('OF', '外野手'),
        ('IF', '內野手'),
        ('UT', '工具人'),
    ]
    
    # MLB 官方球員 ID
    mlb_id = models.IntegerField(
        unique=True, 
        verbose_name="MLB 球員 ID",
        help_text="MLB 官方 API 中的球員識別碼"
    )
    
    # 球員全名
    full_name = models.CharField(
        max_length=100, 
        verbose_name="球員姓名",
        help_text="球員的完整姓名"
    )
    
    # 球員所屬球隊（外鍵關聯到 Team 模型）
    # 使用 SET_NULL 表示如果球隊被刪除，球員記錄不會被刪除，但球隊欄位會被設為 null
    current_team = models.ForeignKey(
        Team, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="目前球隊",
        help_text="球員目前效力的球隊"
    )
    
    # 主要守備位置
    primary_position = models.CharField(
        max_length=3, 
        choices=POSITION_CHOICES, 
        verbose_name="主要位置",
        help_text="球員的主要守備位置"
    )
    
    # 球員照片
    # upload_to 參數指定檔案上傳的目錄
    photo = models.ImageField(
        upload_to='player_photos/', 
        null=True, 
        blank=True,
        verbose_name="球員照片",
        help_text="球員的照片"
    )
    
    # 出生日期
    birth_date = models.DateField(
        null=True, 
        blank=True,
        verbose_name="出生日期"
    )
    
    # 身高（公分）
    height_cm = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(150), MaxValueValidator(250)],
        verbose_name="身高(公分)",
        help_text="球員身高，單位為公分"
    )
    
    # 體重（公斤）
    weight_kg = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(50), MaxValueValidator(200)],
        verbose_name="體重(公斤)",
        help_text="球員體重，單位為公斤"
    )
    
    # 慣用手
    HANDED_CHOICES = [
        ('L', '左投左打'),
        ('R', '右投右打'),
        ('S', '右投左右開弓'),
        ('B', '左右投'),
    ]
    
    bat_hand = models.CharField(
        max_length=1, 
        choices=HANDED_CHOICES, 
        null=True, 
        blank=True,
        verbose_name="打擊慣用手"
    )
    
    # 記錄建立和更新時間
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="建立時間"
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name="更新時間"
    )
    
    class Meta:
        verbose_name = "球員"
        verbose_name_plural = "球員"
        ordering = ['full_name']  # 按球員姓名排序
    
    def __str__(self):
        """
        字串表示方法
        """
        team_name = self.current_team.abbreviation if self.current_team else "FA"
        return f"{self.full_name} ({team_name})"
    
    def get_absolute_url(self):
        """
        取得球員詳細資訊頁面的 URL
        """
        return reverse('mlb_app:player_detail', kwargs={'player_id': self.mlb_id})
    
    @property
    def photo_url(self):
        """
        取得球員照片的 URL
        這是一個屬性方法，讓我們能夠安全地取得照片 URL
        """
        if self.photo and hasattr(self.photo, 'url'):
            return self.photo.url
        else:
            # 如果沒有照片，返回預設的佔位圖片
            return '/static/images/default_player.png'


class GameLog(models.Model):
    """
    比賽記錄模型
    
    這個模型儲存球員在特定比賽中的表現數據。
    它就像是每場比賽的成績單，記錄了球員在那場比賽中的各項統計數據。
    """
    
    # 關聯到球員模型
    player = models.ForeignKey(
        Player, 
        on_delete=models.CASCADE, 
        verbose_name="球員",
        help_text="這場比賽的球員"
    )
    
    # 比賽日期
    game_date = models.DateField(
        verbose_name="比賽日期"
    )
    
    # 對手球隊
    opponent_team = models.ForeignKey(
        Team, 
        on_delete=models.CASCADE, 
        verbose_name="對手球隊",
        help_text="這場比賽的對手"
    )
    
    # 是否為主場比賽
    is_home = models.BooleanField(
        default=True, 
        verbose_name="主場比賽",
        help_text="是否為主場比賽"
    )
    
    # 打擊統計（對打擊手）
    at_bats = models.IntegerField(
        default=0, 
        verbose_name="打數"
    )
    hits = models.IntegerField(
        default=0, 
        verbose_name="安打數"
    )
    runs = models.IntegerField(
        default=0, 
        verbose_name="得分"
    )
    rbi = models.IntegerField(
        default=0, 
        verbose_name="打點"
    )
    home_runs = models.IntegerField(
        default=0, 
        verbose_name="全壘打"
    )
    
    # 投球統計（對投手）
    innings_pitched = models.DecimalField(
        max_digits=4, 
        decimal_places=1, 
        default=0, 
        verbose_name="投球局數"
    )
    strikeouts = models.IntegerField(
        default=0, 
        verbose_name="三振數"
    )
    walks = models.IntegerField(
        default=0, 
        verbose_name="保送數"
    )
    earned_runs = models.IntegerField(
        default=0, 
        verbose_name="自責分"
    )
    
    # 記錄建立時間
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="建立時間"
    )
    
    class Meta:
        verbose_name = "比賽記錄"
        verbose_name_plural = "比賽記錄"
        ordering = ['-game_date']  # 按比賽日期倒序排列
        # 確保同一球員在同一天對同一對手只有一條記錄
        unique_together = ['player', 'game_date', 'opponent_team']
    
    def __str__(self):
        return f"{self.player.full_name} vs {self.opponent_team.abbreviation} ({self.game_date})"
    
    @property
    def batting_average(self):
        """
        計算打擊率
        這是一個屬性方法，當我們存取這個屬性時，它會自動計算打擊率
        """
        if self.at_bats > 0:
            return round(self.hits / self.at_bats, 3)
        return 0.000


class SearchHistory(models.Model):
    """
    搜尋歷史模型
    
    這個模型記錄使用者的搜尋歷史，讓我們能夠：
    1. 提供搜尋建議
    2. 分析熱門搜尋
    3. 改善使用者體驗
    
    想像這就像是圖書館的借閱記錄，幫助我們了解使用者的興趣和需求。
    """
    
    SEARCH_TYPE_CHOICES = [
        ('player', '球員搜尋'),
        ('team', '球隊搜尋'),
        ('game', '比賽搜尋'),
    ]
    
    # 搜尋類型
    search_type = models.CharField(
        max_length=20, 
        choices=SEARCH_TYPE_CHOICES,
        verbose_name="搜尋類型"
    )
    
    # 搜尋關鍵字
    search_query = models.CharField(
        max_length=200, 
        verbose_name="搜尋關鍵字"
    )
    
    # 搜尋結果數量
    results_count = models.IntegerField(
        default=0, 
        verbose_name="結果數量"
    )
    
    # 搜尋時間
    search_time = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="搜尋時間"
    )
    
    # IP 地址（可選）
    ip_address = models.GenericIPAddressField(
        null=True, 
        blank=True,
        verbose_name="IP 地址"
    )
    
    class Meta:
        verbose_name = "搜尋歷史"
        verbose_name_plural = "搜尋歷史"
        ordering = ['-search_time']
    
    def __str__(self):
        return f"{self.search_type}: {self.search_query} ({self.search_time.strftime('%Y-%m-%d %H:%M')})"
