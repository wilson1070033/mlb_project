"""
安全與機器學習配置設定

這個檔案包含了安全防護和機器學習功能的詳細配置。
建議將這些設定放在 Django 的 settings.py 中，或者創建單獨的配置模組。

在實際部署時，敏感資訊（如 API 金鑰）應該使用環境變數或專門的配置管理工具。
"""

import os
from datetime import timedelta

# =============================================================================
# 安全防護設定
# =============================================================================

# API 頻率限制設定
SECURITY_SETTINGS = {
    # 全域頻率限制設定
    'RATE_LIMITING': {
        'DEFAULT_MAX_REQUESTS': 100,          # 預設最大請求數
        'DEFAULT_WINDOW_MINUTES': 10,         # 預設時間視窗（分鐘）
        
        # 針對不同端點的特殊限制
        'ENDPOINT_LIMITS': {
            '/api/': {
                'max_requests': 50,
                'window_minutes': 5
            },
            '/search/': {
                'max_requests': 30,
                'window_minutes': 5
            },
            '/players/': {
                'max_requests': 200,
                'window_minutes': 10
            }
        }
    },
    
    # 輸入驗證設定
    'INPUT_VALIDATION': {
        'MAX_QUERY_LENGTH': 200,              # 搜尋關鍵字最大長度
        'MAX_PLAYER_NAME_LENGTH': 100,        # 球員姓名最大長度
        'ALLOWED_DATE_RANGE_DAYS': 365,       # 允許查詢的日期範圍（天）
        'BLOCKED_KEYWORDS': [                 # 被阻止的關鍵字
            'script', 'alert', 'eval', 'document.cookie'
        ]
    },
    
    # 安全監控設定
    'MONITORING': {
        'LOG_SECURITY_EVENTS': True,          # 是否記錄安全事件
        'ALERT_THRESHOLD': 10,                # 告警閾值
        'SUSPICIOUS_USER_AGENT_PATTERNS': [
            r'sqlmap', r'nikto', r'nmap', r'masscan', r'zap', r'burp'
        ],
        'MAX_ERROR_COUNT_PER_IP': 10,         # 每個 IP 最大錯誤次數
        'ERROR_WINDOW_MINUTES': 10            # 錯誤計數時間視窗
    },
    
    # CSRF 保護增強
    'CSRF_PROTECTION': {
        'REQUIRE_HTTPS_REFERER': True,        # 是否要求 HTTPS Referer
        'TRUSTED_ORIGINS': [                  # 可信任的來源
            'https://localhost:8000',
            'https://127.0.0.1:8000'
        ],
        'VALIDATE_ORIGIN_HEADER': True        # 是否驗證 Origin 標頭
    }
}

# HTTP 安全標頭設定
HTTP_SECURITY_HEADERS = {
    'X-XSS-Protection': '1; mode=block',
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'Content-Security-Policy': (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
        "img-src 'self' data: *; "
        "font-src 'self' cdn.jsdelivr.net; "
        "connect-src 'self' statsapi.mlb.com"
    )
}

# =============================================================================
# 機器學習與 AI 設定
# =============================================================================

# 推薦系統設定
ML_SETTINGS = {
    'RECOMMENDATION_ENGINE': {
        'MODEL_UPDATE_INTERVAL': timedelta(hours=1),    # 模型更新間隔
        'CACHE_TIMEOUT': 3600,                          # 快取超時時間（秒）
        'MAX_RECOMMENDATIONS': 10,                      # 最大推薦數量
        'MIN_SIMILARITY_THRESHOLD': 0.5,               # 最小相似度閾值
        
        # 特徵權重設定
        'FEATURE_WEIGHTS': {
            'position': 0.3,          # 守備位置權重
            'physical': 0.2,          # 身體條件權重
            'performance': 0.4,       # 表現統計權重
            'age': 0.1               # 年齡權重
        },
        
        # 訓練資料設定
        'TRAINING_DATA': {
            'MIN_PLAYERS': 50,        # 最少球員數量
            'UPDATE_THRESHOLD': 100,  # 更新閾值
            'DATA_SOURCES': [
                'popular_players',
                'recent_searches',
                'featured_players'
            ]
        }
    },
    
    # 表現預測設定
    'PERFORMANCE_PREDICTION': {
        'MODEL_TYPE': 'linear_regression',              # 模型類型
        'PREDICTION_CONFIDENCE_THRESHOLD': 0.7,        # 預測信心閾值
        'HISTORICAL_DATA_YEARS': 5,                    # 歷史資料年數
        'FEATURE_SCALING': True,                       # 是否進行特徵縮放
        
        # 預測指標設定
        'PREDICTION_METRICS': [
            'batting_average',
            'home_runs',
            'rbi',
            'era',
            'strikeouts'
        ],
        
        # 年齡影響係數
        'AGE_FACTORS': {
            'peak_age_range': (27, 30),   # 巔峰年齡範圍
            'decline_factor': 0.02,       # 衰退係數
            'young_growth_factor': 0.02   # 年輕成長係數
        }
    },
    
    # 使用者行為分析設定
    'USER_BEHAVIOR_ANALYSIS': {
        'ANALYSIS_WINDOW_DAYS': 30,                    # 分析時間視窗（天）
        'MIN_SEARCHES_FOR_ANALYSIS': 5,               # 分析所需最少搜尋次數
        'ENGAGEMENT_LEVELS': {
            'high': 50,     # 高度參與（搜尋次數）
            'medium': 20,   # 中度參與
            'low': 5        # 低度參與
        },
        
        # 個人化推薦設定
        'PERSONALIZATION': {
            'MAX_RECOMMENDED_TEAMS': 5,
            'MAX_RECOMMENDED_PLAYERS': 8,
            'PREFERENCE_DECAY_DAYS': 7,    # 偏好衰減天數
            'SIMILARITY_ALGORITHM': 'collaborative_filtering'
        }
    }
}

# 資料視覺化設定
VISUALIZATION_SETTINGS = {
    'CHARTS': {
        'DEFAULT_CHART_COLORS': [
            '#3b82f6',  # 藍色
            '#ef4444',  # 紅色
            '#22c55e',  # 綠色
            '#f59e0b',  # 橙色
            '#8b5cf6',  # 紫色
            '#06b6d4',  # 青色
            '#f97316',  # 橙紅色
            '#84cc16'   # 萊姆綠
        ],
        'ANIMATION_DURATION': 1000,        # 動畫持續時間（毫秒）
        'RESPONSIVE': True,                # 是否響應式
        'MAX_DATA_POINTS': 50,            # 最大資料點數
        
        # 圖表類型設定
        'CHART_TYPES': {
            'line': {
                'tension': 0.4,
                'point_radius': 6,
                'border_width': 3
            },
            'radar': {
                'point_radius': 4,
                'border_width': 2,
                'scale_max': 100
            },
            'bar': {
                'border_width': 1,
                'background_opacity': 0.6
            }
        }
    },
    
    # 圖表快取設定
    'CACHING': {
        'CHART_DATA_CACHE_TIMEOUT': 300,   # 圖表資料快取時間（秒）
        'STATIC_CHART_CACHE_TIMEOUT': 3600, # 靜態圖表快取時間
        'ENABLE_CHART_CACHING': True
    }
}

# =============================================================================
# 效能優化設定
# =============================================================================

PERFORMANCE_SETTINGS = {
    # 快取設定
    'CACHING': {
        'DEFAULT_TIMEOUT': 300,            # 預設快取時間（秒）
        'API_CACHE_TIMEOUT': 60,           # API 快取時間
        'PLAYER_DATA_TIMEOUT': 900,        # 球員資料快取時間
        'GAME_DATA_TIMEOUT': 300,          # 比賽資料快取時間
        'ML_MODEL_TIMEOUT': 3600,          # ML 模型快取時間
        
        # 快取鍵前綴
        'CACHE_KEY_PREFIX': 'mlb_app',
        'CACHE_VERSION': 1
    },
    
    # 分頁設定
    'PAGINATION': {
        'DEFAULT_PAGE_SIZE': 25,           # 預設分頁大小
        'MAX_PAGE_SIZE': 100,              # 最大分頁大小
        'SEARCH_RESULTS_PAGE_SIZE': 10,    # 搜尋結果分頁大小
        'API_PAGE_SIZE': 20                # API 分頁大小
    },
    
    # 資料庫優化
    'DATABASE': {
        'USE_SELECT_RELATED': True,        # 使用 select_related 優化
        'USE_PREFETCH_RELATED': True,      # 使用 prefetch_related 優化
        'QUERY_TIMEOUT': 30,               # 查詢超時時間（秒）
        'CONNECTION_MAX_AGE': 600          # 連接最大存活時間（秒）
    }
}

# =============================================================================
# 外部 API 設定
# =============================================================================

EXTERNAL_API_SETTINGS = {
    'MLB_API': {
        'BASE_URL': 'https://statsapi.mlb.com/api/v1',
        'TIMEOUT': 15,                     # 請求超時時間（秒）
        'MAX_RETRIES': 3,                  # 最大重試次數
        'RETRY_DELAY': 1,                  # 重試延遲（秒）
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        
        # 頻率限制
        'RATE_LIMIT': {
            'requests_per_second': 10,
            'requests_per_minute': 600,
            'requests_per_hour': 10000
        },
        
        # 快取設定
        'CACHE_SETTINGS': {
            'games_cache_timeout': 300,     # 比賽資料快取
            'player_cache_timeout': 900,    # 球員資料快取
            'stats_cache_timeout': 600,     # 統計資料快取
            'search_cache_timeout': 600     # 搜尋結果快取
        }
    }
}

# =============================================================================
# 日誌設定
# =============================================================================

LOGGING_SETTINGS = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{',
        },
        'security': {
            'format': '[SECURITY] {asctime} {levelname} {message}',
            'style': '{',
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'logs/mlb_app.log',
            'formatter': 'verbose'
        },
        'security_file': {
            'class': 'logging.FileHandler',
            'filename': 'logs/security.log',
            'formatter': 'security'
        }
    },
    'loggers': {
        'mlb_app': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'mlb_app.security': {
            'handlers': ['console', 'security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'mlb_app.ml_engine': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        }
    }
}

# =============================================================================
# 開發與測試設定
# =============================================================================

DEVELOPMENT_SETTINGS = {
    'DEBUG_ML': False,                      # ML 除錯模式
    'MOCK_API_RESPONSES': False,            # 是否模擬 API 回應
    'ENABLE_PROFILING': False,              # 是否啟用效能分析
    'TEST_DATA_SIZE': 100,                  # 測試資料大小
    
    # 測試設定
    'TESTING': {
        'USE_MOCK_DATA': True,              # 測試時使用模擬資料
        'MOCK_PREDICTION_ACCURACY': 0.85,   # 模擬預測準確度
        'SKIP_EXTERNAL_API_CALLS': True     # 跳過外部 API 呼叫
    }
}

# =============================================================================
# 部署環境設定
# =============================================================================

DEPLOYMENT_SETTINGS = {
    'PRODUCTION': {
        'DEBUG': False,
        'ALLOWED_HOSTS': ['yourdomain.com', 'www.yourdomain.com'],
        'SECURE_SSL_REDIRECT': True,
        'SESSION_COOKIE_SECURE': True,
        'CSRF_COOKIE_SECURE': True,
        'SECURE_BROWSER_XSS_FILTER': True,
        'SECURE_CONTENT_TYPE_NOSNIFF': True
    },
    
    'STAGING': {
        'DEBUG': False,
        'ALLOWED_HOSTS': ['staging.yourdomain.com'],
        'SECURE_SSL_REDIRECT': False,
        'SESSION_COOKIE_SECURE': False,
        'CSRF_COOKIE_SECURE': False
    },
    
    'DEVELOPMENT': {
        'DEBUG': True,
        'ALLOWED_HOSTS': ['localhost', '127.0.0.1'],
        'SECURE_SSL_REDIRECT': False,
        'SESSION_COOKIE_SECURE': False,
        'CSRF_COOKIE_SECURE': False
    }
}

# =============================================================================
# 環境變數設定範例
# =============================================================================

"""
環境變數設定範例 (.env 檔案)：

# Django 設定
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# 資料庫設定
DATABASE_URL=postgresql://user:password@localhost:5432/mlb_db

# 快取設定
REDIS_URL=redis://localhost:6379/0

# 外部 API 設定
MLB_API_KEY=your-mlb-api-key-here
MLB_API_TIMEOUT=15

# 安全設定
SECURITY_RATE_LIMIT_ENABLED=True
SECURITY_MAX_REQUESTS_PER_MINUTE=100

# ML 設定
ML_MODEL_UPDATE_INTERVAL=3600
ML_CACHE_TIMEOUT=1800

# 日誌設定
LOG_LEVEL=INFO
LOG_FILE_PATH=/var/log/mlb_app/app.log

# 監控設定
MONITORING_ENABLED=True
ALERT_EMAIL=admin@yourdomain.com
"""
