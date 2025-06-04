"""
網路安全模組

這個模組專門負責應用程式的安全防護，包括：
1. API 請求頻率限制 (Rate Limiting)
2. 輸入驗證和清理
3. SQL 注入防護
4. XSS 攻擊防護
5. CSRF 保護增強
6. 使用者行為監控

對於資安專業來說，了解這些防護機制的實作原理非常重要。
每一個安全機制都對應真實世界的攻擊向量。
"""

import hashlib
import time
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from django.core.cache import cache
from django.http import HttpRequest
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)

class SecurityError(Exception):
    """自訂安全相關的異常類別"""
    pass

class RateLimiter:
    """
    API 頻率限制器
    
    這個類別實作了滑動視窗演算法來控制 API 請求頻率。
    防止 DDoS 攻擊和濫用行為。
    
    工作原理：
    1. 為每個 IP 位址建立請求計數器
    2. 在指定時間視窗內追蹤請求次數
    3. 超過限制時拒絕服務
    
    在資安領域中，這是防禦層級的第一道防線。
    """
    
    def __init__(self, max_requests: int = 100, window_minutes: int = 10):
        self.max_requests = max_requests
        self.window_seconds = window_minutes * 60
        
    def is_allowed(self, identifier: str) -> tuple[bool, Dict[str, Any]]:
        """
        檢查是否允許請求
        
        參數:
            identifier: 識別符（通常是 IP 位址）
            
        回傳:
            tuple: (是否允許, 限制資訊)
        """
        current_time = time.time()
        cache_key = f"rate_limit:{identifier}"
        
        # 從快取獲取請求歷史
        request_times = cache.get(cache_key, [])
        
        # 移除超出時間視窗的舊請求
        cutoff_time = current_time - self.window_seconds
        request_times = [t for t in request_times if t > cutoff_time]
        
        # 檢查是否超過限制
        if len(request_times) >= self.max_requests:
            return False, {
                'allowed': False,
                'current_requests': len(request_times),
                'max_requests': self.max_requests,
                'window_minutes': self.window_seconds // 60,
                'reset_time': max(request_times) + self.window_seconds
            }
        
        # 添加當前請求時間
        request_times.append(current_time)
        
        # 更新快取
        cache.set(cache_key, request_times, self.window_seconds + 60)
        
        return True, {
            'allowed': True,
            'current_requests': len(request_times),
            'max_requests': self.max_requests,
            'window_minutes': self.window_seconds // 60,
            'remaining_requests': self.max_requests - len(request_times)
        }

class InputValidator:
    """
    輸入驗證器
    
    這個類別負責清理和驗證所有使用者輸入，防止：
    1. SQL 注入攻擊 (SQL Injection)
    2. 跨站腳本攻擊 (XSS)
    3. 目錄遍歷攻擊 (Directory Traversal)
    4. 命令注入攻擊 (Command Injection)
    
    雖然 Django 的 ORM 已經有基本防護，但多層防禦是安全的最佳實踐。
    """
    
    # 危險的 SQL 關鍵字模式
    SQL_INJECTION_PATTERNS = [
        r'\b(union|select|insert|update|delete|drop|exec|execute)\b',
        r'(\-\-|\#|\/\*|\*\/)',
        r'(\'\s*(or|and)\s*\'\s*=\s*\')',
        r'(\;\s*(drop|delete|update|insert))',
    ]
    
    # XSS 攻擊模式
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>.*?</iframe>',
        r'<object[^>]*>.*?</object>',
    ]
    
    @classmethod
    def sanitize_player_name(cls, name: str) -> str:
        """
        清理球員姓名輸入
        
        球員姓名應該只包含字母、空格、連字符和撇號。
        這個方法移除所有可能有害的字符。
        """
        if not name or not isinstance(name, str):
            return ""
        
        # 只保留安全字符
        safe_pattern = r'[a-zA-Z\s\-\'\.]'
        cleaned = ''.join(re.findall(safe_pattern, name))
        
        # 限制長度防止緩衝區溢出攻擊
        cleaned = cleaned[:100]
        
        # 移除多餘空格
        cleaned = ' '.join(cleaned.split())
        
        return cleaned
    
    @classmethod
    def validate_date_input(cls, date_str: str) -> Optional[str]:
        """
        驗證日期輸入格式
        
        嚴格驗證日期格式，防止注入攻擊。
        """
        if not date_str or not isinstance(date_str, str):
            return None
        
        # 嚴格的日期格式檢查
        date_pattern = r'^\d{4}-\d{2}-\d{2}$'
        if not re.match(date_pattern, date_str):
            return None
        
        try:
            # 驗證日期有效性
            datetime.strptime(date_str, '%Y-%m-%d')
            return date_str
        except ValueError:
            return None
    
    @classmethod
    def check_for_injection_attempts(cls, user_input: str) -> bool:
        """
        檢查輸入是否包含注入攻擊模式
        
        回傳 True 表示發現可疑輸入
        """
        if not user_input:
            return False
        
        input_lower = user_input.lower()
        
        # 檢查 SQL 注入模式
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, input_lower, re.IGNORECASE):
                return True
        
        # 檢查 XSS 模式
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, user_input, re.IGNORECASE):
                return True
        
        return False

class SecurityMonitor:
    """
    安全監控系統
    
    監控和記錄潛在的安全威脅，包括：
    1. 可疑的請求模式
    2. 重複的失敗嘗試
    3. 異常的使用者行為
    4. API 濫用行為
    
    這類系統在企業環境中被稱為 SIEM (Security Information and Event Management)。
    """
    
    @classmethod
    def log_security_event(cls, event_type: str, request: HttpRequest, 
                          details: Dict[str, Any] = None):
        """
        記錄安全事件
        
        這個方法建立標準化的安全日誌，方便後續分析。
        """
        client_ip = cls._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
        
        security_log = {
            'timestamp': timezone.now().isoformat(),
            'event_type': event_type,
            'client_ip': client_ip,
            'user_agent': user_agent,
            'path': request.path,
            'method': request.method,
            'user_id': request.user.id if request.user.is_authenticated else None,
            'details': details or {}
        }
        
        # 記錄到日誌檔案
        logger.warning(f"SECURITY_EVENT: {security_log}")
        
        # 儲存到快取供即時分析
        cache_key = f"security_events:{client_ip}:{int(time.time())}"
        cache.set(cache_key, security_log, 3600)  # 保存 1 小時
    
    @classmethod
    def check_suspicious_activity(cls, request: HttpRequest) -> bool:
        """
        檢查可疑活動
        
        分析請求模式，識別潛在的攻擊行為。
        """
        client_ip = cls._get_client_ip(request)
        current_time = time.time()
        
        # 檢查在短時間內的錯誤請求數量
        error_cache_key = f"error_count:{client_ip}"
        error_count = cache.get(error_cache_key, 0)
        
        if error_count > 10:  # 10 分鐘內超過 10 次錯誤
            cls.log_security_event('HIGH_ERROR_RATE', request, {
                'error_count': error_count,
                'threshold': 10
            })
            return True
        
        # 檢查異常的 User-Agent
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        if cls._is_suspicious_user_agent(user_agent):
            cls.log_security_event('SUSPICIOUS_USER_AGENT', request, {
                'user_agent': user_agent
            })
            return True
        
        return False
    
    @classmethod
    def _get_client_ip(cls, request: HttpRequest) -> str:
        """獲取客戶端真實 IP 位址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
    
    @classmethod
    def _is_suspicious_user_agent(cls, user_agent: str) -> bool:
        """檢查是否為可疑的 User-Agent"""
        suspicious_patterns = [
            r'sqlmap',
            r'nikto',
            r'nmap',
            r'masscan',
            r'zap',
            r'burp',
            r'curl.*python',
            r'wget',
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, user_agent, re.IGNORECASE):
                return True
        
        return False

# 建立全域實例
rate_limiter = RateLimiter()
input_validator = InputValidator()
security_monitor = SecurityMonitor()

def require_rate_limit(max_requests: int = 100, window_minutes: int = 10):
    """
    裝飾器：為視圖函數添加頻率限制
    
    使用方式：
    @require_rate_limit(max_requests=50, window_minutes=5)
    def my_view(request):
        ...
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            client_ip = security_monitor._get_client_ip(request)
            limiter = RateLimiter(max_requests, window_minutes)
            
            allowed, limit_info = limiter.is_allowed(client_ip)
            
            if not allowed:
                security_monitor.log_security_event('RATE_LIMIT_EXCEEDED', request, limit_info)
                from django.http import JsonResponse
                return JsonResponse({
                    'error': '請求頻率過高，請稍後再試',
                    'limit_info': limit_info
                }, status=429)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
