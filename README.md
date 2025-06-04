# ⚾ MLB 統計查詢系統

一個功能豐富的Django網頁應用程式，整合了機器學習和資安技術的MLB棒球統計查詢系統。

## 🌟 主要功能

### 📊 數據查詢
- **球員搜尋**: 智慧球員搜尋與自動完成
- **統計數據**: 詳細的打擊、投球、守備統計
- **比賽資訊**: 即時比賽結果和賽程查詢
- **球隊管理**: 球隊資訊和球員名單

### 🤖 AI/機器學習功能
- **智慧推薦**: 基於球員特徵的相似球員推薦
- **表現預測**: 使用機器學習預測球員未來表現
- **行為分析**: 用戶行為分析和個人化內容
- **趨勢分析**: 數據趨勢和熱門球員分析

### 🔒 安全功能
- **頻率限制**: API請求頻率控制，防止DDoS攻擊
- **輸入驗證**: 防止SQL注入和XSS攻擊
- **安全監控**: 可疑活動檢測和安全日誌
- **CSRF保護**: 增強的跨站請求偽造防護

## 🚀 快速開始

### 方法一：使用自動設置腳本（推薦）

#### Windows:
```cmd
setup.bat
```

#### Linux/Mac:
```bash
python setup.py
```

### 方法二：手動設置

1. **克隆專案並進入目錄**
```bash
cd D:\Web\mlb_project
```

2. **啟動虛擬環境**
```bash
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
```

3. **安裝依賴**
```bash
pip install -r requirements.txt
```

4. **設置資料庫**
```bash
python manage.py makemigrations
python manage.py migrate
```

5. **建立管理員帳戶**
```bash
python manage.py createsuperuser
```

6. **收集靜態檔案**
```bash
python manage.py collectstatic
```

7. **啟動伺服器**
```bash
python manage.py runserver
```

8. **訪問網站**
- 主網站: http://127.0.0.1:8000
- 管理後台: http://127.0.0.1:8000/admin

## 📁 專案結構

```
mlb_project/
├── mlb_app/                 # 主要應用程式
│   ├── models.py           # 資料模型
│   ├── views.py            # 視圖函數
│   ├── ai_views.py         # AI功能視圖
│   ├── ml_engine.py        # 機器學習引擎
│   ├── utils.py            # API工具
│   ├── security.py         # 安全模組
│   ├── middleware.py       # 安全中介軟體
│   ├── forms.py            # 表單定義
│   ├── urls.py             # URL配置
│   └── templates/          # 模板檔案
├── static/                 # 靜態檔案
│   ├── css/               # 樣式表
│   └── js/                # JavaScript
├── logs/                  # 日誌檔案
├── media/                 # 媒體檔案
├── requirements.txt       # Python依賴
├── setup.bat             # Windows設置腳本
├── setup.py              # Python設置腳本
└── manage.py             # Django管理腳本
```

## 🔧 配置說明

### API設定
```python
# settings.py
MLB_API_BASE_URL = "https://statsapi.mlb.com/api/v1"
MLB_API_TIMEOUT = 15
MLB_LOCAL_TIMEZONE = 'Asia/Taipei'
```

### 快取設定
- API回應快取: 5分鐘
- ML模型快取: 1小時
- 使用者行為快取: 30分鐘

### 安全設定
- 頻率限制: 每5分鐘30次請求
- 輸入驗證: SQL注入、XSS防護
- 安全標頭: CSP、HSTS等

## 📚 使用說明

### 基本功能
1. **搜尋球員**: 在首頁搜尋框輸入球員姓名
2. **查看統計**: 點擊球員查看詳細統計數據
3. **比賽資訊**: 選擇日期查看當日比賽
4. **球隊資訊**: 瀏覽所有MLB球隊和球員名單

### AI功能
1. **智慧推薦**: 在球員詳細頁面查看相似球員推薦
2. **表現預測**: 查看球員未來表現預測
3. **個人化**: 登入後享受個人化推薦內容

### 管理功能
1. **後台管理**: 訪問 /admin/ 管理數據
2. **用戶管理**: 查看和管理註冊用戶
3. **日誌查看**: 監控系統運行狀況

## 🔍 API端點

### 公開API
- `GET /api/games/` - 獲取比賽資訊
- `GET /api/players/search/` - 球員搜尋
- `GET /api/ai-insights/` - AI洞察數據

### 內部API
- `/players/{id}/` - 球員詳細資訊
- `/players/{id}/stats/` - 球員統計數據
- `/players/{id}/ai-recommendations/` - AI推薦
- `/players/{id}/prediction/` - 表現預測

## 🛡️ 安全功能

### 已實作的防護
- ✅ SQL注入防護
- ✅ XSS攻擊防護
- ✅ CSRF保護
- ✅ 頻率限制
- ✅ 輸入驗證
- ✅ 安全監控
- ✅ 安全標頭

### 監控和日誌
- 安全事件日誌: `logs/security.log`
- 應用程式日誌: `logs/mlb_app.log`
- 即時監控: 可疑活動自動檢測

## 🤖 機器學習功能

### 推薦系統
- **算法**: 基於內容的協同過濾
- **特徵**: 球員位置、統計數據、身體特徵
- **相似度**: 餘弦相似度計算

### 預測模型
- **目標**: 預測球員打擊率和表現
- **特徵**: 歷史數據、年齡、比賽經驗
- **模型**: 線性回歸和隨機森林

### 行為分析
- **用戶畫像**: 基於搜尋歷史分析
- **個人化**: 動態內容推薦
- **趨勢預測**: 熱門內容識別

## 🚀 部署指南

### 開發環境
已配置完成，直接使用 `python manage.py runserver`

### 生產環境
1. 修改 `DEBUG = False`
2. 設定 `ALLOWED_HOSTS`
3. 配置PostgreSQL資料庫
4. 使用Gunicorn + Nginx
5. 設定SSL證書

## 🐛 常見問題

### Q: 無法連接MLB API
A: 檢查網路連接和API設定，確保 `MLB_API_BASE_URL` 正確

### Q: 靜態檔案無法載入
A: 執行 `python manage.py collectstatic`

### Q: AI功能不工作
A: 檢查機器學習套件是否正確安裝，執行 `pip install -r requirements.txt`

### Q: 資料庫錯誤
A: 重新執行遷移：`python manage.py migrate`

## 📖 學習資源

### Django
- [Django官方文檔](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)

### 機器學習
- [scikit-learn](https://scikit-learn.org/)
- [推薦系統教程](https://realpython.com/build-recommendation-engine-collaborative-filtering/)

### 資安
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Django安全指南](https://docs.djangoproject.com/en/stable/topics/security/)

## 🤝 貢獻指南

1. Fork 專案
2. 建立功能分支 (`git checkout -b feature/new-feature`)
3. 提交變更 (`git commit -am 'Add new feature'`)
4. 推送到分支 (`git push origin feature/new-feature`)
5. 建立 Pull Request

## 📄 授權

此專案為教育目的，使用時請遵守MLB API的使用條款。

## 📞 聯絡資訊

如有問題或建議，歡迎聯絡開發團隊。

---

**✨ 享受您的MLB數據探索之旅！**
