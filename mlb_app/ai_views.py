"""
AI 增強功能視圖

這個模組包含了所有使用人工智慧和機器學習的視圖函數。
這些視圖展示了如何將 AI 技術整合到實際的網頁應用程式中。

學習重點：
1. 如何在 Django 中整合機器學習模型
2. 實時推薦系統的實作
3. 使用者行為分析的應用
4. 預測模型的部署和使用

這些技術在現代網路應用中被廣泛使用，例如：
- Netflix 的電影推薦
- Amazon 的商品推薦
- Google 的搜尋建議
- Facebook 的內容個人化
"""

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
import json
import logging
from datetime import datetime, timedelta

from .models import Player, Team, SearchHistory
from .ml_engine import recommendation_engine, performance_predictor, behavior_analyzer
from .utils import mlb_api, MLBAPIError
from .security import require_rate_limit, input_validator

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
@require_rate_limit(max_requests=30, window_minutes=5)  # 使用我們的安全裝飾器
def ai_player_recommendations(request, player_id):
    """
    AI 球員推薦視圖
    
    這個視圖展示了如何使用機器學習為使用者提供個人化的球員推薦。
    
    功能特點：
    1. 基於球員特徵的相似性推薦
    2. 解釋推薦原因
    3. 動態更新推薦模型
    4. 快取優化性能
    
    這種推薦系統在電商、內容平台等領域被廣泛應用。
    """
    context = {
        'player_id': player_id,
        'page_title': '智慧球員推薦'
    }
    
    try:
        # 1. 獲取目標球員資訊
        target_player = mlb_api.get_player_info(player_id)
        if not target_player:
            messages.error(request, "找不到指定的球員")
            return render(request, 'mlb_app/error.html', context)
        
        context['target_player'] = target_player
        context['page_title'] = f"{target_player['fullName']} - 相似球員推薦"
        
        # 2. 檢查推薦模型是否需要更新
        model_last_updated = cache.get('ml_model_last_updated')
        current_time = timezone.now()
        
        if (not model_last_updated or 
            (current_time - model_last_updated).seconds > 3600):  # 1小時更新一次
            
            # 重新訓練模型
            logger.info("更新推薦模型...")
            popular_players_data = _get_training_data()
            recommendation_engine.train_model(popular_players_data)
            cache.set('ml_model_last_updated', current_time, 3600)
        
        # 3. 生成推薦
        recommendations = recommendation_engine.recommend_similar_players(
            target_player_id=int(player_id),
            top_k=8
        )
        
        # 4. 豐富推薦資訊
        enriched_recommendations = []
        for rec in recommendations:
            try:
                rec_player_info = mlb_api.get_player_info(rec['player_id'])
                if rec_player_info:
                    enriched_rec = {
                        'player_info': rec_player_info,
                        'similarity_score': round(rec['similarity_score'] * 100, 1),
                        'recommendation_reason': rec['recommendation_reason'],
                        'confidence_level': _calculate_confidence_level(rec['similarity_score'])
                    }
                    enriched_recommendations.append(enriched_rec)
            except Exception as e:
                logger.warning(f"獲取推薦球員 {rec['player_id']} 資訊失敗: {str(e)}")
                continue
        
        context['recommendations'] = enriched_recommendations
        context['total_recommendations'] = len(enriched_recommendations)
        
        # 5. 記錄使用者行為（用於未來的行為分析）
        if request.user.is_authenticated:
            SearchHistory.objects.create(
                search_type='ai_recommendation',
                search_query=f"similar_to_{player_id}",
                results_count=len(enriched_recommendations),
                ip_address=_get_client_ip(request)
            )
        
        logger.info(f"成功生成 {len(enriched_recommendations)} 個球員推薦")
        
    except MLBAPIError as e:
        logger.error(f"AI 推薦過程中發生 API 錯誤: {str(e)}")
        messages.error(request, f"獲取推薦時發生錯誤：{str(e)}")
        context['recommendations'] = []
        context['total_recommendations'] = 0
        
    except Exception as e:
        logger.error(f"AI 推薦過程中發生未預期錯誤: {str(e)}")
        messages.error(request, "生成推薦時發生錯誤，請稍後再試")
        context['recommendations'] = []
        context['total_recommendations'] = 0
    
    return render(request, 'mlb_app/ai_recommendations.html', context)


@require_http_methods(["GET"])
@require_rate_limit(max_requests=20, window_minutes=5)
def ai_performance_prediction(request, player_id):
    """
    AI 球員表現預測視圖
    
    這個視圖展示了如何使用預測模型來預測球員未來的表現。
    
    預測模型的應用場景：
    1. 球團的球員評估
    2. 夢幻體育的選手選擇
    3. 投資決策的輔助分析
    4. 媒體報導的數據支持
    
    重要概念：
    - 特徵工程：選擇影響預測的重要變數
    - 模型驗證：確保預測的可靠性
    - 不確定性量化：提供預測的信心區間
    """
    context = {
        'player_id': player_id,
        'page_title': '球員表現預測'
    }
    
    try:
        # 1. 獲取球員基本資訊
        player_info = mlb_api.get_player_info(player_id)
        if not player_info:
            messages.error(request, "找不到指定的球員")
            return render(request, 'mlb_app/error.html', context)
        
        context['player_info'] = player_info
        context['page_title'] = f"{player_info['fullName']} - 表現預測"
        
        # 2. 獲取歷史統計數據
        current_year = str(timezone.now().year)
        hitting_stats = mlb_api.get_player_stats(int(player_id), 'hitting', 'yearByYear')
        
        # 3. 準備預測特徵
        prediction_features = _prepare_prediction_features(player_info, hitting_stats)
        
        # 4. 生成預測
        predicted_avg, confidence_interval = performance_predictor.predict_batting_average(
            prediction_features
        )
        
        # 5. 計算預測等級和建議
        prediction_analysis = _analyze_prediction(predicted_avg, confidence_interval, prediction_features)
        
        context.update({
            'predicted_avg': round(predicted_avg, 3),
            'confidence_interval': round(confidence_interval, 3),
            'prediction_analysis': prediction_analysis,
            'historical_data': hitting_stats[:5],  # 只顯示最近5年
            'prediction_date': timezone.now().date(),
            'features_used': list(prediction_features.keys())
        })
        
        # 6. 記錄預測請求
        if request.user.is_authenticated:
            SearchHistory.objects.create(
                search_type='ai_prediction',
                search_query=f"predict_{player_id}",
                results_count=1,
                ip_address=_get_client_ip(request)
            )
        
        logger.info(f"成功生成球員 {player_id} 的表現預測")
        
    except MLBAPIError as e:
        logger.error(f"預測過程中發生 API 錯誤: {str(e)}")
        messages.error(request, f"獲取預測資料時發生錯誤：{str(e)}")
        context['prediction_error'] = True
        
    except Exception as e:
        logger.error(f"預測過程中發生未預期錯誤: {str(e)}")
        messages.error(request, "生成預測時發生錯誤，請稍後再試")
        context['prediction_error'] = True
    
    return render(request, 'mlb_app/ai_prediction.html', context)


@login_required
@require_http_methods(["GET"])
def user_dashboard(request):
    """
    使用者個人化儀表板
    
    這個視圖展示了如何使用行為分析來建立個人化的使用者體驗。
    
    個人化系統的核心概念：
    1. 使用者畫像建立：基於歷史行為分析使用者興趣
    2. 內容個人化：根據興趣推薦相關內容
    3. 介面適應：調整介面以符合使用者習慣
    4. 預測性服務：預測使用者可能感興趣的內容
    
    這種個人化體驗是現代網路服務的核心競爭力。
    """
    context = {
        'page_title': '我的個人化儀表板'
    }
    
    try:
        user_id = str(request.user.id)
        
        # 1. 獲取使用者搜尋歷史
        user_searches = SearchHistory.objects.filter(
            ip_address=_get_client_ip(request)
        ).order_by('-search_time')[:50]  # 最近50次搜尋
        
        search_history = [
            {
                'search_type': search.search_type,
                'search_query': search.search_query,
                'search_time': search.search_time.isoformat(),
                'results_count': search.results_count
            }
            for search in user_searches
        ]
        
        # 2. 分析使用者行為
        user_profile = behavior_analyzer.analyze_search_patterns(user_id, search_history)
        
        # 3. 基於行為分析生成個人化推薦
        personalized_content = _generate_personalized_content(user_profile)
        
        # 4. 獲取使用者統計
        user_stats = {
            'total_searches': len(search_history),
            'favorite_search_type': _get_most_frequent_search_type(search_history),
            'peak_activity_hour': user_profile.get('peak_search_hours', [19])[0],
            'engagement_level': user_profile.get('engagement_level', 'new'),
            'member_since': request.user.date_joined.strftime('%Y-%m-%d')
        }
        
        context.update({
            'user_profile': user_profile,
            'personalized_content': personalized_content,
            'user_stats': user_stats,
            'recent_searches': search_history[:10]  # 最近10次搜尋
        })
        
        logger.info(f"載入使用者 {user_id} 的個人化儀表板")
        
    except Exception as e:
        logger.error(f"載入使用者儀表板時發生錯誤: {str(e)}")
        messages.error(request, "載入個人化內容時發生錯誤")
        context['dashboard_error'] = True
    
    return render(request, 'mlb_app/user_dashboard.html', context)


@require_http_methods(["GET"])
@cache_page(60 * 10)  # 快取10分鐘
def ai_insights_api(request):
    """
    AI 洞察 API 端點
    
    這個 API 提供即時的 AI 分析結果，供前端 JavaScript 使用。
    展示了如何建立 RESTful API 來服務機器學習模型。
    
    API 設計原則：
    1. 快速回應：使用快取和優化的演算法
    2. 錯誤處理：提供清楚的錯誤訊息
    3. 版本控制：支援 API 版本管理
    4. 限流保護：防止濫用
    """
    try:
        insight_type = request.GET.get('type', 'trends')
        
        if insight_type == 'trends':
            # 分析搜尋趨勢
            insights = _analyze_search_trends()
        elif insight_type == 'popular_players':
            # 分析熱門球員
            insights = _analyze_popular_players()
        elif insight_type == 'team_performance':
            # 分析球隊表現趨勢
            insights = _analyze_team_performance()
        else:
            return JsonResponse({
                'success': False,
                'error': '不支援的洞察類型'
            }, status=400)
        
        return JsonResponse({
            'success': True,
            'insight_type': insight_type,
            'data': insights,
            'generated_at': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"生成 AI 洞察時發生錯誤: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': '生成洞察時發生內部錯誤'
        }, status=500)


# 輔助函數

def _get_training_data():
    """獲取訓練推薦模型所需的數據"""
    # 這裡應該從資料庫或 API 獲取大量球員數據
    # 目前使用一些知名球員作為示例
    popular_names = [
        'Shohei Ohtani', 'Aaron Judge', 'Mookie Betts', 'Fernando Tatis Jr.',
        'Mike Trout', 'Ronald Acuna Jr.', 'Manny Machado', 'Juan Soto',
        'Gerrit Cole', 'Jacob deGrom', 'Max Scherzer', 'Shane Bieber'
    ]
    
    all_players_data = []
    for name in popular_names:
        try:
            players = mlb_api.search_player(name)
            if players:
                # 為每個球員添加一些模擬的統計數據
                player_data = players[0].copy()
                player_data['stats'] = _generate_mock_stats()
                all_players_data.append(player_data)
        except:
            continue
    
    return all_players_data

def _generate_mock_stats():
    """生成模擬的統計數據（實際應用中應從真實 API 獲取）"""
    import random
    return {
        'avg': round(random.uniform(0.200, 0.350), 3),
        'homeRuns': random.randint(5, 50),
        'rbi': random.randint(20, 130),
        'era': round(random.uniform(2.50, 5.00), 2),
        'strikeOuts': random.randint(50, 300)
    }

def _calculate_confidence_level(similarity_score):
    """計算推薦的信心等級"""
    if similarity_score >= 0.8:
        return 'high'
    elif similarity_score >= 0.6:
        return 'medium'
    else:
        return 'low'

def _prepare_prediction_features(player_info, hitting_stats):
    """準備預測模型所需的特徵"""
    features = {}
    
    # 基本特徵
    if player_info.get('birthDate'):
        birth_date = datetime.strptime(player_info['birthDate'], '%Y-%m-%d')
        age = (datetime.now() - birth_date).days / 365.25
        features['age'] = age
    else:
        features['age'] = 25
    
    # 歷史表現特徵
    if hitting_stats:
        recent_stats = hitting_stats[0].get('stat', {})
        features['career_avg'] = float(recent_stats.get('avg', 0.250))
        features['games_played'] = int(recent_stats.get('gamesPlayed', 150))
        features['at_bats'] = int(recent_stats.get('atBats', 500))
    else:
        features.update({
            'career_avg': 0.250,
            'games_played': 150,
            'at_bats': 500
        })
    
    return features

def _analyze_prediction(predicted_avg, confidence_interval, features):
    """分析預測結果並提供解釋"""
    analysis = {
        'prediction_quality': 'good',
        'key_factors': [],
        'risk_factors': [],
        'outlook': 'neutral'
    }
    
    # 分析年齡因素
    age = features.get('age', 25)
    if age < 25:
        analysis['key_factors'].append('年輕球員，具有成長潛力')
        analysis['outlook'] = 'positive'
    elif age > 32:
        analysis['risk_factors'].append('年齡較大，可能面臨體能下滑')
        analysis['outlook'] = 'cautious'
    
    # 分析預測信心
    if confidence_interval > 0.1:
        analysis['prediction_quality'] = 'uncertain'
        analysis['risk_factors'].append('預測不確定性較高')
    
    return analysis

def _generate_personalized_content(user_profile):
    """基於使用者檔案生成個人化內容"""
    content = {
        'recommended_players': [],
        'suggested_teams': [],
        'trending_topics': [],
        'custom_insights': []
    }
    
    # 基於偏好球隊推薦內容
    preferred_teams = user_profile.get('preferred_teams', [])
    for team in preferred_teams[:3]:
        content['suggested_teams'].append({
            'team_name': team,
            'reason': f'基於您對 {team} 的搜尋歷史'
        })
    
    # 基於參與度推薦功能
    engagement_level = user_profile.get('engagement_level', 'new')
    if engagement_level == 'high':
        content['custom_insights'].append('探索進階統計分析功能')
        content['custom_insights'].append('查看 AI 球員表現預測')
    elif engagement_level == 'medium':
        content['custom_insights'].append('嘗試球員比較功能')
    else:
        content['custom_insights'].append('開始探索您感興趣的球隊')
    
    return content

def _get_most_frequent_search_type(search_history):
    """獲取最常搜尋的類型"""
    from collections import Counter
    search_types = [s.get('search_type') for s in search_history if s.get('search_type')]
    if search_types:
        return Counter(search_types).most_common(1)[0][0]
    return 'player'

def _analyze_search_trends():
    """分析搜尋趨勢"""
    # 簡化的趨勢分析
    return {
        'trending_players': ['Shohei Ohtani', 'Aaron Judge', 'Ronald Acuna Jr.'],
        'trending_teams': ['Los Angeles Dodgers', 'New York Yankees'],
        'hot_topics': ['季後賽預測', '新人王競爭', 'MVP 候選人']
    }

def _analyze_popular_players():
    """分析熱門球員"""
    return {
        'most_searched': ['Shohei Ohtani', 'Aaron Judge', 'Mookie Betts'],
        'rising_stars': ['Julio Rodriguez', 'Bobby Witt Jr.', 'Spencer Torkelson'],
        'veteran_leaders': ['Mike Trout', 'Manny Machado', 'Paul Goldschmidt']
    }

def _analyze_team_performance():
    """分析球隊表現趨勢"""
    return {
        'top_performers': ['Los Angeles Dodgers', 'Houston Astros', 'New York Yankees'],
        'improving_teams': ['Baltimore Orioles', 'Seattle Mariners'],
        'struggling_teams': ['Oakland Athletics', 'Kansas City Royals']
    }

def _get_client_ip(request):
    """獲取客戶端 IP 位址"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
