"""
訓練和更新機器學習模型的管理命令

這個命令用於訓練、更新和管理 MLB 統計系統中的機器學習模型。
它展示了如何：
1. 整合機器學習工作流程到 Django 中
2. 批量數據處理和模型訓練
3. 模型版本管理和部署
4. 性能監控和評估

使用方法：
python manage.py train_ml_models
python manage.py train_ml_models --model recommendation
python manage.py train_ml_models --force-retrain
python manage.py train_ml_models --evaluate-only
"""

import time
import json
import pickle
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from django.core.management.base import BaseCommand, CommandError
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings

from mlb_app.models import Player, Team, SearchHistory
from mlb_app.ml_engine import recommendation_engine, performance_predictor, behavior_analyzer
from mlb_app.utils import mlb_api, MLBAPIError

logger = logging.getLogger('mlb_app.ml_engine')


class Command(BaseCommand):
    """
    機器學習模型訓練和管理命令
    
    這個命令負責管理整個 ML 流水線，包括：
    - 數據準備和清理
    - 模型訓練和驗證
    - 模型部署和版本管理
    - 性能監控和評估
    """
    
    help = '訓練和更新機器學習模型'
    
    def add_arguments(self, parser):
        """定義命令行參數"""
        parser.add_argument(
            '--model',
            type=str,
            choices=['recommendation', 'prediction', 'behavior', 'all'],
            default='all',
            help='指定要訓練的模型類型',
        )
        
        parser.add_argument(
            '--force-retrain',
            action='store_true',
            help='強制重新訓練模型，即使已有最新版本',
        )
        
        parser.add_argument(
            '--evaluate-only',
            action='store_true',
            help='只評估現有模型，不進行訓練',
        )
        
        parser.add_argument(
            '--data-size',
            type=int,
            help='限制訓練數據大小（用於測試）',
        )
        
        parser.add_argument(
            '--save-metrics',
            action='store_true',
            help='保存模型性能指標到檔案',
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='顯示詳細的訓練過程',
        )
    
    def handle(self, *args, **options):
        """命令主要執行邏輯"""
        start_time = time.time()
        self.verbose = options['verbose']
        
        self.stdout.write("🤖 開始機器學習模型管理流程")
        
        try:
            # 檢查是否只是評估模式
            if options['evaluate_only']:
                self._evaluate_models(options['model'])
                return
            
            # 選擇要訓練的模型
            models_to_train = self._get_models_to_train(options['model'])
            
            if not models_to_train:
                raise CommandError("沒有可訓練的模型")
            
            self.stdout.write(f"📋 準備訓練 {len(models_to_train)} 個模型")
            
            # 準備訓練數據
            training_data = self._prepare_training_data(options.get('data_size'))
            
            if not training_data:
                raise CommandError("無法準備訓練數據")
            
            # 訓練每個模型
            results = {}
            for model_name in models_to_train:
                self.stdout.write(f"\n🏋️ 開始訓練 {model_name} 模型")
                
                try:
                    result = self._train_model(
                        model_name, 
                        training_data, 
                        options['force_retrain']
                    )
                    results[model_name] = result
                    
                    self.stdout.write(
                        self.style.SUCCESS(f"✅ {model_name} 模型訓練完成")
                    )
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"❌ {model_name} 模型訓練失敗: {str(e)}")
                    )
                    logger.error(f"訓練 {model_name} 模型時發生錯誤: {str(e)}")
                    results[model_name] = {'status': 'failed', 'error': str(e)}
            
            # 顯示總結
            elapsed_time = time.time() - start_time
            self._show_training_summary(results, elapsed_time)
            
            # 保存指標（如果需要）
            if options['save_metrics']:
                self._save_training_metrics(results)
            
        except Exception as e:
            logger.error(f"ML 模型訓練過程中發生錯誤: {str(e)}")
            raise CommandError(f"訓練失敗: {str(e)}")
    
    def _get_models_to_train(self, model_filter: str) -> List[str]:
        """獲取要訓練的模型列表"""
        all_models = ['recommendation', 'prediction', 'behavior']
        
        if model_filter == 'all':
            return all_models
        elif model_filter in all_models:
            return [model_filter]
        else:
            return []
    
    def _prepare_training_data(self, data_size_limit: Optional[int]) -> Dict[str, Any]:
        """
        準備訓練數據
        
        這個方法從資料庫和 API 收集訓練所需的數據。
        """
        self.stdout.write("📊 準備訓練數據...")
        
        training_data = {
            'players': [],
            'search_history': [],
            'user_behavior': [],
            'timestamp': timezone.now()
        }
        
        try:
            # 1. 獲取球員數據
            self.stdout.write("   📥 收集球員數據...")
            
            # 從資料庫獲取現有球員
            players_from_db = list(Player.objects.all())
            
            if self.verbose:
                self.stdout.write(f"   從資料庫獲取 {len(players_from_db)} 位球員")
            
            # 從 API 獲取熱門球員數據
            api_players = self._fetch_players_from_api(data_size_limit)
            
            if self.verbose:
                self.stdout.write(f"   從 API 獲取 {len(api_players)} 位球員")
            
            # 合併球員數據
            training_data['players'] = self._merge_player_data(players_from_db, api_players)
            
            # 2. 獲取搜尋歷史
            self.stdout.write("   🔍 收集搜尋歷史...")
            
            search_limit = data_size_limit if data_size_limit else 1000
            recent_searches = SearchHistory.objects.all()[:search_limit]
            
            training_data['search_history'] = [
                {
                    'search_type': search.search_type,
                    'search_query': search.search_query,
                    'results_count': search.results_count,
                    'search_time': search.search_time.isoformat(),
                    'ip_address': search.ip_address
                }
                for search in recent_searches
            ]
            
            # 3. 準備用戶行為數據
            self.stdout.write("   👤 分析用戶行為...")
            
            training_data['user_behavior'] = self._prepare_user_behavior_data(
                training_data['search_history']
            )
            
            self.stdout.write(
                f"   ✅ 數據準備完成: {len(training_data['players'])} 位球員, "
                f"{len(training_data['search_history'])} 條搜尋記錄"
            )
            
            return training_data
            
        except Exception as e:
            logger.error(f"準備訓練數據時發生錯誤: {str(e)}")
            raise
    
    def _fetch_players_from_api(self, limit: Optional[int]) -> List[Dict[str, Any]]:
        """從 MLB API 獲取球員數據"""
        popular_names = [
            'Shohei Ohtani', 'Aaron Judge', 'Mookie Betts', 'Fernando Tatis Jr.',
            'Mike Trout', 'Ronald Acuna Jr.', 'Manny Machado', 'Juan Soto',
            'Gerrit Cole', 'Jacob deGrom', 'Max Scherzer', 'Shane Bieber',
            'Vladimir Guerrero Jr.', 'Bo Bichette', 'George Springer'
        ]
        
        if limit:
            popular_names = popular_names[:limit]
        
        players_data = []
        for name in popular_names:
            try:
                players = mlb_api.search_player(name)
                if players:
                    # 為每個球員添加模擬的統計數據
                    player_data = players[0].copy()
                    player_data['stats'] = self._generate_mock_stats()
                    players_data.append(player_data)
                    
                # 避免 API 頻率限制
                time.sleep(0.1)
                
            except Exception as e:
                if self.verbose:
                    self.stdout.write(f"   ⚠️  獲取球員 {name} 失敗: {str(e)}")
                continue
        
        return players_data
    
    def _generate_mock_stats(self) -> Dict[str, Any]:
        """生成模擬的統計數據"""
        import random
        return {
            'avg': round(random.uniform(0.200, 0.350), 3),
            'homeRuns': random.randint(5, 50),
            'rbi': random.randint(20, 130),
            'runs': random.randint(30, 120),
            'hits': random.randint(50, 200),
            'era': round(random.uniform(2.50, 5.00), 2),
            'strikeOuts': random.randint(50, 300),
            'wins': random.randint(5, 20),
            'saves': random.randint(0, 40),
        }
    
    def _merge_player_data(self, db_players: List[Player], api_players: List[Dict]) -> List[Dict]:
        """合併資料庫和 API 的球員數據"""
        merged_data = []
        
        # 轉換資料庫球員數據為字典格式
        for player in db_players:
            player_dict = {
                'id': player.mlb_id,
                'fullName': player.full_name,
                'currentTeam': player.current_team.name if player.current_team else 'Unknown',
                'primaryPosition': player.primary_position,
                'birthDate': player.birth_date.isoformat() if player.birth_date else None,
                'height': f"{player.height_cm} cm" if player.height_cm else None,
                'weight': f"{player.weight_kg} kg" if player.weight_kg else None,
                'stats': self._generate_mock_stats()  # 在實際應用中應該從真實數據獲取
            }
            merged_data.append(player_dict)
        
        # 添加 API 球員數據（避免重複）
        existing_ids = {player.mlb_id for player in db_players}
        for api_player in api_players:
            if api_player.get('id') not in existing_ids:
                merged_data.append(api_player)
        
        return merged_data
    
    def _prepare_user_behavior_data(self, search_history: List[Dict]) -> List[Dict]:
        """準備用戶行為分析數據"""
        # 按 IP 分組搜尋歷史
        user_sessions = {}
        
        for search in search_history:
            ip = search.get('ip_address', 'unknown')
            if ip not in user_sessions:
                user_sessions[ip] = []
            user_sessions[ip].append(search)
        
        # 分析每個用戶的行為模式
        behavior_data = []
        for ip, searches in user_sessions.items():
            if len(searches) >= 3:  # 只分析有足夠搜尋記錄的用戶
                behavior_profile = {
                    'user_id': ip,
                    'search_count': len(searches),
                    'search_types': [s.get('search_type') for s in searches],
                    'search_queries': [s.get('search_query') for s in searches],
                    'time_span_hours': self._calculate_time_span(searches),
                    'engagement_level': 'high' if len(searches) > 10 else 'medium' if len(searches) > 5 else 'low'
                }
                behavior_data.append(behavior_profile)
        
        return behavior_data
    
    def _calculate_time_span(self, searches: List[Dict]) -> float:
        """計算搜尋時間跨度（小時）"""
        try:
            times = [datetime.fromisoformat(s['search_time'].replace('Z', '+00:00')) for s in searches if s.get('search_time')]
            if len(times) < 2:
                return 0
            return (max(times) - min(times)).total_seconds() / 3600
        except:
            return 0
    
    def _train_model(self, model_name: str, training_data: Dict, force_retrain: bool) -> Dict[str, Any]:
        """
        訓練指定的模型
        
        返回訓練結果和性能指標
        """
        result = {
            'status': 'success',
            'model_name': model_name,
            'training_time': 0,
            'metrics': {}
        }
        
        start_time = time.time()
        
        try:
            if model_name == 'recommendation':
                result['metrics'] = self._train_recommendation_model(
                    training_data['players'], force_retrain
                )
            
            elif model_name == 'prediction':
                result['metrics'] = self._train_prediction_model(
                    training_data['players'], force_retrain
                )
            
            elif model_name == 'behavior':
                result['metrics'] = self._train_behavior_model(
                    training_data['user_behavior'], force_retrain
                )
            
            result['training_time'] = time.time() - start_time
            
        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
            raise
        
        return result
    
    def _train_recommendation_model(self, players_data: List[Dict], force_retrain: bool) -> Dict:
        """訓練推薦模型"""
        if self.verbose:
            self.stdout.write("   🔄 正在訓練推薦引擎...")
        
        # 檢查是否需要重新訓練
        if not force_retrain:
            last_update = cache.get('ml_model_last_updated')
            if last_update and (timezone.now() - last_update).seconds < 3600:
                return {'status': 'skipped', 'reason': 'recently_updated'}
        
        # 訓練模型
        recommendation_engine.train_model(players_data)
        
        # 評估模型（簡化版本）
        metrics = {
            'training_samples': len(players_data),
            'features_count': len(players_data[0]) if players_data else 0,
            'model_size_mb': 0.5,  # 模擬值
            'accuracy_score': 0.85,  # 模擬值
        }
        
        # 更新快取時間戳
        cache.set('ml_model_last_updated', timezone.now(), 7200)
        
        return metrics
    
    def _train_prediction_model(self, players_data: List[Dict], force_retrain: bool) -> Dict:
        """訓練預測模型"""
        if self.verbose:
            self.stdout.write("   📈 正在訓練預測模型...")
        
        # 這裡應該實作實際的模型訓練邏輯
        # 目前返回模擬的指標
        metrics = {
            'training_samples': len(players_data),
            'test_accuracy': 0.78,  # 模擬值
            'mean_absolute_error': 0.025,  # 模擬值
            'r2_score': 0.72,  # 模擬值
        }
        
        return metrics
    
    def _train_behavior_model(self, behavior_data: List[Dict], force_retrain: bool) -> Dict:
        """訓練用戶行為分析模型"""
        if self.verbose:
            self.stdout.write("   👥 正在訓練行為分析模型...")
        
        # 這裡應該實作實際的行為分析邏輯
        metrics = {
            'user_profiles': len(behavior_data),
            'clustering_accuracy': 0.82,  # 模擬值
            'prediction_precision': 0.76,  # 模擬值
        }
        
        return metrics
    
    def _evaluate_models(self, model_filter: str):
        """評估現有模型"""
        self.stdout.write("📊 評估現有模型...")
        
        models_to_evaluate = self._get_models_to_train(model_filter)
        
        for model_name in models_to_evaluate:
            self.stdout.write(f"\n🔍 評估 {model_name} 模型:")
            
            try:
                metrics = self._get_model_metrics(model_name)
                
                for metric_name, value in metrics.items():
                    self.stdout.write(f"   {metric_name}: {value}")
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"   ❌ 評估失敗: {str(e)}")
                )
    
    def _get_model_metrics(self, model_name: str) -> Dict[str, Any]:
        """獲取模型性能指標"""
        # 這裡應該返回實際的模型指標
        # 目前返回模擬數據
        return {
            'last_updated': cache.get('ml_model_last_updated', '未知'),
            'status': '活躍',
            'accuracy': '85%',
            'data_freshness': '1 小時前'
        }
    
    def _show_training_summary(self, results: Dict, elapsed_time: float):
        """顯示訓練總結"""
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("🎯 模型訓練完成！"))
        self.stdout.write(f"⏱️  總執行時間: {elapsed_time:.2f} 秒")
        
        successful = sum(1 for r in results.values() if r.get('status') == 'success')
        failed = len(results) - successful
        
        self.stdout.write(f"✅ 成功: {successful} 個模型")
        if failed > 0:
            self.stdout.write(f"❌ 失敗: {failed} 個模型")
        
        # 顯示詳細結果
        for model_name, result in results.items():
            if result.get('status') == 'success':
                metrics = result.get('metrics', {})
                training_time = result.get('training_time', 0)
                
                self.stdout.write(f"\n📊 {model_name} 模型:")
                self.stdout.write(f"   訓練時間: {training_time:.2f} 秒")
                
                for metric_name, value in metrics.items():
                    self.stdout.write(f"   {metric_name}: {value}")
    
    def _save_training_metrics(self, results: Dict):
        """保存訓練指標到檔案"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"ml_training_metrics_{timestamp}.json"
        
        metrics_data = {
            'timestamp': timestamp,
            'results': results,
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(metrics_data, f, indent=2, ensure_ascii=False, default=str)
            
            self.stdout.write(f"💾 訓練指標已保存到: {filename}")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"保存指標時發生錯誤: {str(e)}")
            )
