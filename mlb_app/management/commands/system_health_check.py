"""
系統健康狀態檢查命令

這個命令用於檢查 MLB 統計系統的各個組件狀態，包括：
1. 資料庫連接和數據完整性
2. 外部 API 可用性
3. 快取系統狀態
4. 機器學習模型狀態
5. 安全設定檢查
6. 性能指標監控

這是一個很好的運維工具，幫助快速診斷系統問題。

使用方法：
python manage.py system_health_check
python manage.py system_health_check --component database
python manage.py system_health_check --detailed
python manage.py system_health_check --export-report
"""

import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings
from django.test import Client

from mlb_app.models import Player, Team, SearchHistory
from mlb_app.utils import mlb_api, MLBAPIError
from mlb_app.ml_engine import recommendation_engine

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    系統健康狀態檢查命令
    
    這個命令提供全面的系統診斷功能，幫助運維人員快速了解系統狀態。
    """
    
    help = '檢查系統各組件的健康狀態'
    
    def add_arguments(self, parser):
        """定義命令行參數"""
        parser.add_argument(
            '--component',
            type=str,
            choices=['database', 'api', 'cache', 'ml', 'security', 'all'],
            default='all',
            help='指定要檢查的組件',
        )
        
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='顯示詳細的檢查結果',
        )
        
        parser.add_argument(
            '--export-report',
            action='store_true',
            help='將檢查結果導出為 JSON 報告',
        )
        
        parser.add_argument(
            '--threshold',
            type=float,
            default=5.0,
            help='響應時間閾值（秒），超過此值視為警告',
        )
    
    def handle(self, *args, **options):
        """命令主要執行邏輯"""
        start_time = time.time()
        self.detailed = options['detailed']
        self.threshold = options['threshold']
        
        self.stdout.write("🔍 開始系統健康狀態檢查...\n")
        
        # 選擇要檢查的組件
        components = self._get_components_to_check(options['component'])
        
        # 執行檢查
        results = {}
        overall_status = 'healthy'
        
        for component in components:
            self.stdout.write(f"📊 檢查 {component} 組件...")
            
            try:
                result = self._check_component(component)
                results[component] = result
                
                # 更新整體狀態
                if result['status'] == 'error':
                    overall_status = 'error'
                elif result['status'] == 'warning' and overall_status == 'healthy':
                    overall_status = 'warning'
                
                # 顯示結果
                self._display_component_result(component, result)
                
            except Exception as e:
                error_result = {
                    'status': 'error',
                    'message': f'檢查失敗: {str(e)}',
                    'timestamp': timezone.now().isoformat()
                }
                results[component] = error_result
                overall_status = 'error'
                
                self.stdout.write(
                    self.style.ERROR(f"   ❌ {component} 檢查失敗: {str(e)}")
                )
        
        # 計算總執行時間
        total_time = time.time() - start_time
        
        # 顯示總結
        self._display_summary(results, overall_status, total_time)
        
        # 導出報告（如果需要）
        if options['export_report']:
            self._export_report(results, overall_status, total_time)
    
    def _get_components_to_check(self, component_filter: str) -> List[str]:
        """獲取要檢查的組件列表"""
        all_components = ['database', 'api', 'cache', 'ml', 'security']
        
        if component_filter == 'all':
            return all_components
        elif component_filter in all_components:
            return [component_filter]
        else:
            return all_components
    
    def _check_component(self, component: str) -> Dict[str, Any]:
        """檢查指定組件"""
        check_methods = {
            'database': self._check_database,
            'api': self._check_external_api,
            'cache': self._check_cache_system,
            'ml': self._check_ml_models,
            'security': self._check_security_settings,
        }
        
        method = check_methods.get(component)
        if method:
            return method()
        else:
            return {
                'status': 'error',
                'message': f'未知組件: {component}',
                'timestamp': timezone.now().isoformat()
            }
    
    def _check_database(self) -> Dict[str, Any]:
        """檢查資料庫連接和數據完整性"""
        start_time = time.time()
        result = {
            'status': 'healthy',
            'message': '資料庫運行正常',
            'details': {},
            'timestamp': timezone.now().isoformat()
        }
        
        try:
            # 1. 檢查資料庫連接
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                connection_time = time.time() - start_time
                
                if connection_time > self.threshold:
                    result['status'] = 'warning'
                    result['message'] = f'資料庫連接緩慢 ({connection_time:.2f}s)'
            
            # 2. 檢查數據表
            table_stats = {}
            
            # 球員數據
            player_count = Player.objects.count()
            table_stats['players'] = player_count
            
            # 球隊數據
            team_count = Team.objects.count()
            table_stats['teams'] = team_count
            
            # 搜尋歷史
            search_count = SearchHistory.objects.count()
            table_stats['search_history'] = search_count
            
            result['details']['table_stats'] = table_stats
            result['details']['connection_time'] = f"{connection_time:.3f}s"
            
            # 3. 檢查數據完整性
            integrity_issues = []
            
            # 檢查球員是否有球隊
            players_without_team = Player.objects.filter(current_team__isnull=True).count()
            if players_without_team > 0:
                integrity_issues.append(f"{players_without_team} 位球員沒有球隊資訊")
            
            # 檢查最近數據更新
            recent_searches = SearchHistory.objects.filter(
                search_time__gte=timezone.now() - timedelta(days=1)
            ).count()
            
            if recent_searches == 0:
                integrity_issues.append("過去24小時沒有搜尋記錄")
            
            if integrity_issues:
                result['details']['integrity_issues'] = integrity_issues
                if result['status'] == 'healthy':
                    result['status'] = 'warning'
                    result['message'] = '發現數據完整性問題'
            
            # 4. 檢查資料庫大小和性能
            try:
                with connection.cursor() as cursor:
                    # SQLite 特定的查詢
                    cursor.execute("PRAGMA database_list")
                    db_info = cursor.fetchall()
                    
                    if db_info:
                        result['details']['database_info'] = str(db_info[0])
                        
            except Exception as e:
                result['details']['db_size_check_error'] = str(e)
            
        except Exception as e:
            result['status'] = 'error'
            result['message'] = f'資料庫檢查失敗: {str(e)}'
            result['details']['error'] = str(e)
        
        return result
    
    def _check_external_api(self) -> Dict[str, Any]:
        """檢查外部 API 可用性"""
        start_time = time.time()
        result = {
            'status': 'healthy',
            'message': 'API 服務正常',
            'details': {},
            'timestamp': timezone.now().isoformat()
        }
        
        try:
            # 測試 MLB API
            test_response_time = time.time()
            test_players = mlb_api.search_player('Ohtani')
            api_response_time = time.time() - test_response_time
            
            result['details']['api_response_time'] = f"{api_response_time:.3f}s"
            result['details']['test_query_results'] = len(test_players) if test_players else 0
            
            if api_response_time > self.threshold:
                result['status'] = 'warning'
                result['message'] = f'API 響應緩慢 ({api_response_time:.2f}s)'
            
            if not test_players:
                result['status'] = 'warning'
                result['message'] = 'API 查詢沒有返回結果'
            
            # 檢查 API 限制
            try:
                # 連續發送幾個請求測試頻率限制
                for i in range(3):
                    mlb_api.search_player(f'test{i}')
                    time.sleep(0.1)
                
                result['details']['rate_limit_test'] = '通過'
                
            except Exception as e:
                result['details']['rate_limit_test'] = f'失敗: {str(e)}'
                if 'rate limit' in str(e).lower():
                    result['status'] = 'warning'
                    result['message'] = 'API 頻率限制觸發'
            
        except MLBAPIError as e:
            result['status'] = 'error'
            result['message'] = f'MLB API 錯誤: {str(e)}'
            result['details']['api_error'] = str(e)
            
        except Exception as e:
            result['status'] = 'error'
            result['message'] = f'API 檢查失敗: {str(e)}'
            result['details']['error'] = str(e)
        
        return result
    
    def _check_cache_system(self) -> Dict[str, Any]:
        """檢查快取系統狀態"""
        result = {
            'status': 'healthy',
            'message': '快取系統正常',
            'details': {},
            'timestamp': timezone.now().isoformat()
        }
        
        try:
            # 測試基本快取操作
            test_key = 'health_check_test'
            test_value = f'test_value_{int(time.time())}'
            
            # 寫入測試
            cache.set(test_key, test_value, 60)
            
            # 讀取測試
            cached_value = cache.get(test_key)
            
            if cached_value == test_value:
                result['details']['basic_operations'] = '正常'
            else:
                result['status'] = 'warning'
                result['message'] = '快取讀寫測試失敗'
                result['details']['basic_operations'] = '失敗'
            
            # 清理測試
            cache.delete(test_key)
            
            # 檢查快取統計
            cache_stats = {}
            
            # 檢查一些已知的快取鍵
            known_keys = [
                'mlb_popular_players',
                'ml_recommendation_model',
                'ml_model_last_updated'
            ]
            
            for key in known_keys:
                value = cache.get(key)
                cache_stats[key] = 'exists' if value is not None else 'missing'
            
            result['details']['cache_keys'] = cache_stats
            
            # 快取配置檢查
            cache_config = getattr(settings, 'CACHES', {})
            if cache_config:
                default_cache = cache_config.get('default', {})
                result['details']['cache_backend'] = default_cache.get('BACKEND', 'unknown')
                result['details']['cache_timeout'] = default_cache.get('TIMEOUT', 'unknown')
            
        except Exception as e:
            result['status'] = 'error'
            result['message'] = f'快取系統檢查失敗: {str(e)}'
            result['details']['error'] = str(e)
        
        return result
    
    def _check_ml_models(self) -> Dict[str, Any]:
        """檢查機器學習模型狀態"""
        result = {
            'status': 'healthy',
            'message': 'ML 模型正常',
            'details': {},
            'timestamp': timezone.now().isoformat()
        }
        
        try:
            model_status = {}
            
            # 檢查推薦模型
            try:
                # 檢查模型是否已訓練
                last_update = cache.get('ml_model_last_updated')
                if last_update:
                    time_since_update = timezone.now() - last_update
                    model_status['recommendation_model'] = {
                        'status': 'active',
                        'last_update': last_update.isoformat(),
                        'hours_since_update': time_since_update.total_seconds() / 3600
                    }
                    
                    # 如果超過24小時沒更新，標記為警告
                    if time_since_update.total_seconds() > 86400:
                        model_status['recommendation_model']['status'] = 'outdated'
                        result['status'] = 'warning'
                        result['message'] = '推薦模型需要更新'
                else:
                    model_status['recommendation_model'] = {
                        'status': 'not_trained',
                        'message': '模型尚未訓練'
                    }
                    result['status'] = 'warning'
                    result['message'] = 'ML 模型未初始化'
                
                # 測試推薦功能
                if recommendation_engine.similarity_matrix is not None:
                    model_status['recommendation_test'] = '功能正常'
                else:
                    model_status['recommendation_test'] = '需要初始化'
                    if result['status'] == 'healthy':
                        result['status'] = 'warning'
                
            except Exception as e:
                model_status['recommendation_model'] = {
                    'status': 'error',
                    'error': str(e)
                }
                result['status'] = 'error'
                result['message'] = f'推薦模型檢查失敗: {str(e)}'
            
            result['details']['models'] = model_status
            
            # 檢查訓練數據
            player_count = Player.objects.count()
            if player_count < 10:
                result['details']['training_data_warning'] = f'球員數據不足 ({player_count} 位)'
                if result['status'] == 'healthy':
                    result['status'] = 'warning'
            
        except Exception as e:
            result['status'] = 'error'
            result['message'] = f'ML 模型檢查失敗: {str(e)}'
            result['details']['error'] = str(e)
        
        return result
    
    def _check_security_settings(self) -> Dict[str, Any]:
        """檢查安全設定"""
        result = {
            'status': 'healthy',
            'message': '安全設定正常',
            'details': {},
            'timestamp': timezone.now().isoformat()
        }
        
        security_issues = []
        security_warnings = []
        
        try:
            # 檢查 Django 設定
            if getattr(settings, 'DEBUG', False):
                security_issues.append('DEBUG 模式在生產環境中應該關閉')
            
            if getattr(settings, 'SECRET_KEY', '').startswith('django-insecure'):
                security_issues.append('使用預設的不安全 SECRET_KEY')
            
            # 檢查 ALLOWED_HOSTS
            allowed_hosts = getattr(settings, 'ALLOWED_HOSTS', [])
            if '*' in allowed_hosts:
                security_warnings.append('ALLOWED_HOSTS 包含通配符，在生產環境中不安全')
            
            # 檢查 HTTPS 設定
            if not getattr(settings, 'SECURE_SSL_REDIRECT', False):
                security_warnings.append('未啟用 HTTPS 重定向')
            
            if not getattr(settings, 'SESSION_COOKIE_SECURE', False):
                security_warnings.append('Session Cookie 未設定為 Secure')
            
            # 檢查安全標頭
            if not getattr(settings, 'SECURE_BROWSER_XSS_FILTER', False):
                security_warnings.append('未啟用 XSS 過濾器')
            
            # 檢查中介軟體
            middleware = getattr(settings, 'MIDDLEWARE', [])\n            
            security_middleware_found = any('SecurityMiddleware' in mw for mw in middleware)
            if not security_middleware_found:
                security_warnings.append('未發現自定義安全中介軟體')
            
            # 彙總結果
            result['details']['security_issues'] = security_issues
            result['details']['security_warnings'] = security_warnings
            
            if security_issues:
                result['status'] = 'error'
                result['message'] = f'發現 {len(security_issues)} 個安全問題'
            elif security_warnings:
                result['status'] = 'warning'
                result['message'] = f'發現 {len(security_warnings)} 個安全警告'
            
            # 檢查密碼驗證設定
            auth_validators = getattr(settings, 'AUTH_PASSWORD_VALIDATORS', [])
            result['details']['password_validators'] = len(auth_validators)
            
            if len(auth_validators) < 3:
                security_warnings.append('密碼驗證規則不足')
            
        except Exception as e:
            result['status'] = 'error'
            result['message'] = f'安全檢查失敗: {str(e)}'
            result['details']['error'] = str(e)
        
        return result
    
    def _display_component_result(self, component: str, result: Dict[str, Any]):
        """顯示組件檢查結果"""
        status = result['status']
        message = result['message']
        
        # 選擇顯示樣式
        if status == 'healthy':
            style = self.style.SUCCESS
            icon = '✅'
        elif status == 'warning':
            style = self.style.WARNING
            icon = '⚠️'
        else:
            style = self.style.ERROR
            icon = '❌'
        
        self.stdout.write(f"   {style(icon + ' ' + message)}")
        
        # 顯示詳細資訊
        if self.detailed and result.get('details'):
            details = result['details']
            for key, value in details.items():
                if isinstance(value, (list, dict)):
                    self.stdout.write(f"     {key}: {json.dumps(value, ensure_ascii=False)}")
                else:
                    self.stdout.write(f"     {key}: {value}")
    
    def _display_summary(self, results: Dict, overall_status: str, total_time: float):
        """顯示檢查總結"""
        self.stdout.write("\n" + "="*60)
        
        # 整體狀態
        if overall_status == 'healthy':
            style = self.style.SUCCESS
            icon = '🟢'
            message = '系統運行正常'
        elif overall_status == 'warning':
            style = self.style.WARNING
            icon = '🟡'
            message = '系統運行正常，但有警告'
        else:
            style = self.style.ERROR
            icon = '🔴'
            message = '系統存在問題，需要處理'
        
        self.stdout.write(style(f"{icon} 系統整體狀態: {message}"))
        self.stdout.write(f"⏱️  檢查耗時: {total_time:.2f} 秒")
        
        # 組件狀態統計
        healthy_count = sum(1 for r in results.values() if r['status'] == 'healthy')
        warning_count = sum(1 for r in results.values() if r['status'] == 'warning')
        error_count = sum(1 for r in results.values() if r['status'] == 'error')
        
        self.stdout.write(f"📊 組件狀態: {healthy_count} 正常, {warning_count} 警告, {error_count} 錯誤")
        
        # 建議操作
        if error_count > 0:
            self.stdout.write("\n🔧 建議操作:")
            self.stdout.write("   1. 檢查錯誤日誌獲取詳細資訊")
            self.stdout.write("   2. 修復標記為錯誤的組件")
            self.stdout.write("   3. 重新執行健康檢查確認修復")
        
        elif warning_count > 0:
            self.stdout.write("\n💡 建議改進:")
            self.stdout.write("   1. 檢查警告項目並評估影響")
            self.stdout.write("   2. 在適當時候進行優化")
            self.stdout.write("   3. 定期監控系統狀態")
    
    def _export_report(self, results: Dict, overall_status: str, total_time: float):
        """導出檢查報告"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"system_health_report_{timestamp}.json"
        
        report = {
            'timestamp': timestamp,
            'overall_status': overall_status,
            'total_check_time': total_time,
            'component_results': results,
            'summary': {
                'healthy_count': sum(1 for r in results.values() if r['status'] == 'healthy'),
                'warning_count': sum(1 for r in results.values() if r['status'] == 'warning'),
                'error_count': sum(1 for r in results.values() if r['status'] == 'error'),
            }
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            
            self.stdout.write(f"\n💾 健康檢查報告已導出: {filename}")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"導出報告時發生錯誤: {str(e)}")
            )
