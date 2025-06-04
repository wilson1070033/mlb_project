"""
安全中介軟體

這個中介軟體在每個 HTTP 請求進入 Django 應用程式時進行安全檢查。
中介軟體是 Django 的一個重要概念，它允許我們在請求處理的不同階段插入自訂邏輯。

在資安領域中，中介軟體扮演了「看門狗」的角色，確保每個進入系統的請求都經過適當的安全檢查。
這種設計模式被稱為「縱深防禦」(Defense in Depth)。

工作流程：
1. 請求進入 → 安全檢查 → 處理請求 → 回傳回應
2. 任何階段發現威脅都會立即阻止並記錄
"""

from django.http import HttpResponseForbidden, JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from .security import security_monitor, input_validator, rate_limiter
import json
import logging

logger = logging.getLogger(__name__)

class SecurityMiddleware(MiddlewareMixin):
    """
    安全防護中介軟體
    
    這個中介軟體整合了多層安全防護機制，包括：
    - 輸入驗證和清理
    - 可疑活動監控
    - 頻率限制（針對特定端點）
    - 安全標頭設定
    """
    
    # 需要頻率限制的端點
    RATE_LIMITED_PATHS = [
        '/api/',
        '/search/',
        '/player/',
    ]
    
    # 需要嚴格輸入驗證的參數
    VALIDATED_PARAMS = ['q', 'query', 'search', 'name', 'date']
    
    def process_request(self, request):
        """
        處理進入的請求
        
        這個方法在 Django 處理請求之前執行，
        確保所有請求都經過安全檢查。
        """
        # 1. 檢查可疑活動
        if security_monitor.check_suspicious_activity(request):
            client_ip = security_monitor._get_client_ip(request)
            logger.warning(f"阻止來自 {client_ip} 的可疑請求")
            return HttpResponseForbidden("Access denied due to suspicious activity")
        
        # 2. 輸入驗證
        violation = self._validate_inputs(request)
        if violation:
            security_monitor.log_security_event('INPUT_VALIDATION_FAILED', request, violation)
            return JsonResponse({
                'error': '輸入格式不正確',
                'details': '請檢查輸入內容是否包含特殊字符'
            }, status=400)
        
        # 3. 針對特定路徑進行頻率限制
        if self._should_rate_limit(request.path):
            client_ip = security_monitor._get_client_ip(request)
            allowed, limit_info = rate_limiter.is_allowed(client_ip)
            
            if not allowed:
                security_monitor.log_security_event('RATE_LIMIT_EXCEEDED', request, limit_info)
                return JsonResponse({
                    'error': '請求頻率過高，請稍後再試',
                    'retry_after': 60
                }, status=429)
        
        return None  # 繼續處理請求
    
    def process_response(self, request, response):
        """
        處理回應
        
        在回應返回給客戶端之前，添加安全相關的 HTTP 標頭。
        這些標頭能夠防止多種客戶端攻擊。
        """
        # 設定安全標頭
        self._set_security_headers(response)
        
        # 記錄異常回應
        if response.status_code >= 400:
            self._log_error_response(request, response)
        
        return response
    
    def _validate_inputs(self, request):
        """
        驗證請求參數
        
        檢查所有輸入參數是否包含潛在的攻擊模式。
        回傳違規資訊，如果沒有問題則回傳 None。
        """
        # 檢查 GET 參數
        for param_name in self.VALIDATED_PARAMS:
            value = request.GET.get(param_name)
            if value and input_validator.check_for_injection_attempts(value):
                return {
                    'type': 'injection_attempt',
                    'parameter': param_name,
                    'value': value[:100]  # 只記錄前100個字符
                }
        
        # 檢查 POST 資料
        if request.method == 'POST':
            try:
                if hasattr(request, 'body') and request.body:
                    # 檢查 JSON 資料
                    if request.content_type == 'application/json':
                        try:
                            data = json.loads(request.body)
                            for key, value in data.items():
                                if isinstance(value, str) and input_validator.check_for_injection_attempts(value):
                                    return {
                                        'type': 'json_injection_attempt',
                                        'field': key,
                                        'value': value[:100]
                                    }
                        except json.JSONDecodeError:
                            pass
                    
                    # 檢查表單資料
                    for param_name in self.VALIDATED_PARAMS:
                        value = request.POST.get(param_name)
                        if value and input_validator.check_for_injection_attempts(value):
                            return {
                                'type': 'form_injection_attempt',
                                'parameter': param_name,
                                'value': value[:100]
                            }
            except Exception as e:
                logger.error(f"輸入驗證時發生錯誤: {str(e)}")
        
        return None
    
    def _should_rate_limit(self, path):
        """
        判斷是否需要對該路徑進行頻率限制
        """
        return any(path.startswith(limited_path) for limited_path in self.RATE_LIMITED_PATHS)
    
    def _set_security_headers(self, response):
        """
        設定安全相關的 HTTP 標頭
        
        這些標頭能夠防止多種攻擊：
        - XSS (跨站腳本攻擊)
        - Clickjacking (點擊劫持)
        - MIME 類型混淆攻擊
        - 協議降級攻擊
        """
        # 防止 XSS 攻擊
        response['X-XSS-Protection'] = '1; mode=block'
        
        # 防止 MIME 類型嗅探
        response['X-Content-Type-Options'] = 'nosniff'
        
        # 防止點擊劫持攻擊
        response['X-Frame-Options'] = 'DENY'
        
        # 內容安全政策 (CSP)
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
            "img-src 'self' data: *; "
            "font-src 'self' cdn.jsdelivr.net; "
            "connect-src 'self' statsapi.mlb.com"
        )
        
        # 強制 HTTPS (在生產環境中)
        if getattr(settings, 'SECURE_SSL_REDIRECT', False):
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # 移除敏感的伺服器資訊
        if 'Server' in response:
            del response['Server']
    
    def _log_error_response(self, request, response):
        """
        記錄錯誤回應
        
        分析錯誤模式，幫助識別潛在的攻擊行為。
        """
        client_ip = security_monitor._get_client_ip(request)
        
        # 增加錯誤計數器
        error_cache_key = f"error_count:{client_ip}"
        from django.core.cache import cache
        error_count = cache.get(error_cache_key, 0) + 1
        cache.set(error_cache_key, error_count, 600)  # 10 分鐘
        
        # 記錄特別異常的錯誤
        if response.status_code in [403, 404, 500]:
            security_monitor.log_security_event('ERROR_RESPONSE', request, {
                'status_code': response.status_code,
                'error_count': error_count
            })


class CSRFEnhancementMiddleware(MiddlewareMixin):
    """
    CSRF 保護增強中介軟體
    
    雖然 Django 已經內建 CSRF 保護，但這個中介軟體提供額外的防護層。
    CSRF (Cross-Site Request Forgery) 是一種常見的網路攻擊手法。
    """
    
    def process_request(self, request):
        """
        增強 CSRF 檢查
        
        檢查請求來源是否可信，防止跨站請求偽造攻擊。
        """
        # 對於狀態改變的操作，進行額外的來源檢查
        if request.method in ['POST', 'PUT', 'DELETE']:
            if not self._validate_origin(request):
                security_monitor.log_security_event('INVALID_ORIGIN', request, {
                    'referer': request.META.get('HTTP_REFERER'),
                    'origin': request.META.get('HTTP_ORIGIN')
                })
                return JsonResponse({
                    'error': '無效的請求來源'
                }, status=403)
        
        return None
    
    def _validate_origin(self, request):
        """
        驗證請求來源
        
        檢查 HTTP Referer 和 Origin 標頭是否來自可信的來源。
        """
        referer = request.META.get('HTTP_REFERER', '')
        origin = request.META.get('HTTP_ORIGIN', '')
        
        # 獲取允許的主機名稱
        allowed_hosts = getattr(settings, 'ALLOWED_HOSTS', [])
        
        # 如果是 AJAX 請求，檢查 Origin
        if origin:
            from urllib.parse import urlparse
            origin_host = urlparse(origin).netloc
            return any(host == '*' or origin_host == host or origin_host.endswith('.' + host) 
                      for host in allowed_hosts)
        
        # 檢查 Referer
        if referer:
            from urllib.parse import urlparse
            referer_host = urlparse(referer).netloc
            return any(host == '*' or referer_host == host or referer_host.endswith('.' + host) 
                      for host in allowed_hosts)
        
        # 如果都沒有，可能是直接存取，允許但記錄
        return True
