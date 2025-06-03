"""
Django 視圖模組

這個模組包含了所有處理 HTTP 請求的視圖函數和類別。
視圖就像是應用程式的控制中心，負責：

1. 接收使用者的 HTTP 請求
2. 調用適當的業務邏輯（例如 API 查詢）
3. 處理數據和錯誤
4. 渲染模板並返回 HTTP 回應

每個視圖都有特定的職責，就像餐廳中的不同服務生負責不同的桌位一樣。
這種分工讓程式碼更加組織化，也更容易維護和測試。

視圖的設計原則：
- 保持視圖函數簡潔，主要負責協調工作
- 將複雜的業務邏輯放在 utils 或 models 中
- 提供良好的錯誤處理
- 使用適當的 HTTP 狀態碼
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import login # Added for registration
import json
import logging
from datetime import datetime, timedelta

from .models import Player, Team, GameLog, SearchHistory
from .utils import mlb_api, MLBAPIError, get_today_games, get_popular_players, format_stat_value
from .forms import UserRegisterForm # Added for registration

# 設定日誌記錄器
logger = logging.getLogger(__name__)


def index(request):
    """
    首頁視圖
    
    這是網站的主頁面，展示今天的比賽和熱門球員。
    它就像是報紙的頭版，展示最重要和最新的資訊。
    
    功能：
    - 顯示今天的 MLB 比賽
    - 展示熱門球員
    - 提供搜尋入口
    - 顯示應用程式的主要功能導航
    """
    context = {
        'page_title': 'MLB 統計查詢系統',
        'current_date': timezone.now().date(),
    }
    
    try:
        # 獲取今天的比賽資訊
        # 使用快取來提高性能，避免重複的 API 請求
        today_games = get_today_games()
        context['today_games'] = today_games[:6]  # 只顯示前6場比賽
        context['total_games_today'] = len(today_games)
        
        # 獲取熱門球員
        popular_players = get_popular_players()
        context['popular_players'] = popular_players[:5]  # 只顯示前5位球員
        
        logger.info(f"首頁載入成功：{len(today_games)} 場比賽，{len(popular_players)} 位熱門球員")
        
    except MLBAPIError as e:
        logger.error(f"載入首頁數據時發生 API 錯誤: {str(e)}")
        messages.error(request, f"獲取最新資訊時發生錯誤：{str(e)}")
        # 即使 API 失敗，我們仍然顯示頁面，只是沒有即時數據
        context['today_games'] = []
        context['popular_players'] = []
        
    except Exception as e:
        logger.error(f"載入首頁時發生未預期錯誤: {str(e)}")
        messages.error(request, "載入頁面時發生錯誤，請稍後再試。")
        context['today_games'] = []
        context['popular_players'] = []
    
    return render(request, 'mlb_app/index.html', context)


@require_http_methods(["GET"])
def games_by_date(request):
    """
    按日期查詢比賽的視圖
    
    這個視圖處理特定日期的比賽查詢請求。
    使用者可以選擇任何日期來查看當天的比賽安排和結果。
    
    URL 參數：
    - date: YYYY-MM-DD 格式的日期字串
    
    功能：
    - 驗證日期格式
    - 查詢指定日期的比賽
    - 處理無比賽的情況
    - 提供錯誤處理
    """
    # 從 URL 參數獲取日期
    date_str = request.GET.get('date')
    
    # 如果沒有提供日期，預設為今天
    if not date_str:
        date_str = timezone.now().date().strftime('%Y-%m-%d')
    
    # 驗證日期格式
    try:
        query_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # 檢查日期是否合理（不能查詢太久以前或太久以後的比賽）
        today = timezone.now().date()
        if query_date < (today - timedelta(days=365)):
            messages.warning(request, "查詢日期過於久遠，可能沒有詳細數據。")
        elif query_date > (today + timedelta(days=30)):
            messages.warning(request, "查詢日期過於未來，比賽安排可能會變動。")
            
    except ValueError:
        messages.error(request, "日期格式錯誤，請使用 YYYY-MM-DD 格式。")
        return redirect('mlb_app:index')
    
    context = {
        'page_title': f'{date_str} 比賽資訊',
        'query_date': query_date,
        'date_str': date_str,
    }
    
    try:
        # 查詢比賽資訊
        games = mlb_api.get_games_by_date(date_str)
        context['games'] = games
        context['total_games'] = len(games)
        
        # 記錄搜尋歷史
        SearchHistory.objects.create(
            search_type='game',
            search_query=date_str,
            results_count=len(games),
            ip_address=get_client_ip(request)
        )
        
        if games:
            logger.info(f"查詢到 {len(games)} 場比賽：{date_str}")
        else:
            messages.info(request, f"{date_str} 沒有安排比賽。")
            
    except MLBAPIError as e:
        logger.error(f"查詢比賽時發生 API 錯誤: {str(e)}")
        messages.error(request, f"查詢比賽資訊時發生錯誤：{str(e)}")
        context['games'] = []
        context['total_games'] = 0
        
    except Exception as e:
        logger.error(f"查詢比賽時發生未預期錯誤: {str(e)}")
        messages.error(request, "查詢比賽時發生錯誤，請稍後再試。")
        context['games'] = []
        context['total_games'] = 0
    
    return render(request, 'mlb_app/games.html', context)


@require_http_methods(["GET"])
def search_players(request):
    """
    球員搜尋視圖
    
    這個視圖處理球員搜尋請求。使用者可以輸入球員姓名來查找球員資訊。
    搜尋支援模糊匹配，並提供搜尋建議。
    
    URL 參數：
    - q: 搜尋關鍵字（球員姓名）
    - page: 分頁號碼
    
    功能：
    - 處理搜尋查詢
    - 分頁顯示結果
    - 記錄搜尋歷史
    - 提供搜尋建議
    """
    query = request.GET.get('q', '').strip()
    page = request.GET.get('page', 1)
    
    search_suggestions = ["Shohei Ohtani", "Aaron Judge", "Mookie Betts", "Fernando Tatis Jr.", "Mike Trout", "Ronald Acuna Jr.", "Manny Machado", "Juan Soto"]

    context = {
        'page_title': '球員搜尋',
        'query': query,
        'search_suggestions': search_suggestions,
    }
    
    if not query:
        # 如果沒有搜尋關鍵字，顯示熱門球員
        try:
            popular_players = get_popular_players()
            context['players'] = popular_players
            context['is_popular'] = True
            context['total_results'] = len(popular_players)
        except Exception as e:
            logger.error(f"獲取熱門球員時發生錯誤: {str(e)}")
            context['players'] = []
            context['total_results'] = 0
            
        return render(request, 'mlb_app/search_players.html', context)
    
    # 驗證搜尋關鍵字
    if len(query) < 2:
        messages.warning(request, "請輸入至少2個字符進行搜尋。")
        # Even if query is too short, we still want to pass suggestions
        return render(request, 'mlb_app/search_players.html', context)
    
    try:
        # 執行搜尋
        players = mlb_api.search_player(query)
        
        # 記錄搜尋歷史
        SearchHistory.objects.create(
            search_type='player',
            search_query=query,
            results_count=len(players),
            ip_address=get_client_ip(request)
        )
        
        # 分頁處理
        paginator = Paginator(players, 10)  # 每頁顯示10個結果
        
        try:
            players_page = paginator.page(page)
        except PageNotAnInteger:
            players_page = paginator.page(1)
        except EmptyPage:
            players_page = paginator.page(paginator.num_pages)
        
        context.update({
            'players': players_page,
            'total_results': len(players),
            'paginator': paginator,
            'is_paginated': paginator.num_pages > 1,
        })
        
        if players:
            logger.info(f"球員搜尋 '{query}' 找到 {len(players)} 個結果")
        else:
            messages.info(request, f"沒有找到與 '{query}' 相關的球員。")
            
    except MLBAPIError as e:
        logger.error(f"搜尋球員時發生 API 錯誤: {str(e)}")
        messages.error(request, f"搜尋球員時發生錯誤：{str(e)}")
        context['players'] = []
        context['total_results'] = 0
        
    except Exception as e:
        logger.error(f"搜尋球員時發生未預期錯誤: {str(e)}")
        messages.error(request, "搜尋時發生錯誤，請稍後再試。")
        context['players'] = []
        context['total_results'] = 0
    
    return render(request, 'mlb_app/search_players.html', context)


@require_http_methods(["GET"])
def player_detail(request, player_id):
    """
    球員詳細資訊視圖
    
    這個視圖顯示特定球員的詳細資訊和統計數據。
    它是球員資訊的完整展示頁面。
    
    URL 參數：
    - player_id: 球員的 MLB ID
    
    功能：
    - 顯示球員基本資訊
    - 展示各項統計數據
    - 提供統計圖表
    - 顯示歷史表現
    """
    context = {
        'player_id': player_id,
        'quick_stats': None,
        'quick_stats_type': None,
        'recent_performance_available': False, # Placeholder for future implementation
    }

    try:
        # 1. Fetch Full Player Info
        player_info = mlb_api.get_player_info(player_id)
        if not player_info:
            logger.warning(f"Player info not found for ID {player_id} in player_detail view.")
            raise Http404("找不到該球員的詳細資訊 (Info)")

        context['player_info'] = player_info
        context['page_title'] = f"{player_info.get('fullName', player_id)} 詳細資訊"

        # 2. Fetch Stats for Quick Stats and other sections
        # We fetch both hitting and pitching for the latest season to determine quick stats
        # Use current year for season stats by default for quick_stats
        current_year = str(timezone.now().year)
        hitting_stats_season = mlb_api.get_player_stats(player_id, 'hitting', 'season', season=current_year)
        pitching_stats_season = mlb_api.get_player_stats(player_id, 'pitching', 'season', season=current_year)

        # Prepare "Quick Stats" Data
        if hitting_stats_season and hitting_stats_season[0].get('stat'):
            hs = hitting_stats_season[0]['stat']
            # Check for meaningful hitting activity, e.g. more than 10 ABs or some hits/HRs
            if hs.get('atBats', 0) > 10 or hs.get('hits', 0) > 0 or hs.get('homeRuns', 0) > 0:
                context['quick_stats'] = {
                    'season': hitting_stats_season[0].get('season', current_year),
                    'team': hitting_stats_season[0].get('team', {}).get('name', 'N/A'),
                    'gamesPlayed': hs.get('gamesPlayed'),
                    'atBats': hs.get('atBats'),
                    'runs': hs.get('runs'),
                    'hits': hs.get('hits'),
                    'homeRuns': hs.get('homeRuns'),
                    'rbi': hs.get('rbi'),
                    'avg': format_stat_value(hs.get('avg'), 'avg'), # Use formatter
                    'ops': format_stat_value(hs.get('ops'), 'ops'), # Use formatter
                }
                context['quick_stats_type'] = 'hitting'

        if context['quick_stats_type'] is None and pitching_stats_season and pitching_stats_season[0].get('stat'):
            ps = pitching_stats_season[0]['stat']
            # Check for meaningful pitching activity, e.g., has pitched some innings or games
            if ps.get('inningsPitched', "0.0") != "0.0" or ps.get('gamesPitched', 0) > 0 :
                context['quick_stats'] = {
                    'season': pitching_stats_season[0].get('season', current_year),
                    'team': pitching_stats_season[0].get('team', {}).get('name', 'N/A'),
                    'wins': ps.get('wins'),
                    'losses': ps.get('losses'),
                    'era': format_stat_value(ps.get('era'), 'era'), # Use formatter
                    'gamesPitched': ps.get('gamesPitched'),
                    'gamesStarted': ps.get('gamesStarted'),
                    'inningsPitched': ps.get('inningsPitched'),
                    'strikeOuts': ps.get('strikeOuts'),
                    'whip': format_stat_value(ps.get('whip'), 'whip'), # Use formatter
                }
                context['quick_stats_type'] = 'pitching'

        # For other parts of the page, you might want career stats or allow user to select
        # For now, let's fetch general hitting/pitching/fielding stats (yearByYear or career as default)
        # These are illustrative; the player_stats view already handles detailed stat fetching.
        # This view's primary purpose is the overview.
        context['hitting_stats_summary'] = mlb_api.get_player_stats(player_id, 'hitting', 'yearByYear')
        context['pitching_stats_summary'] = mlb_api.get_player_stats(player_id, 'pitching', 'yearByYear')
        context['fielding_stats_summary'] = mlb_api.get_player_stats(player_id, 'fielding', 'yearByYear')

        logger.info(f"載入球員 {player_id} ({player_info.get('fullName', 'N/A')}) 的詳細資訊")
        
    except MLBAPIError as e:
        logger.error(f"獲取球員詳細資訊時發生 API 錯誤: {str(e)}")
        messages.error(request, f"獲取球員資訊時發生錯誤：{str(e)}")
        raise Http404("無法獲取球員資訊")
        
    except Exception as e:
        logger.error(f"載入球員詳細資訊時發生未預期錯誤: {str(e)}")
        messages.error(request, "載入球員資訊時發生錯誤。")
        raise Http404("載入球員資訊失敗")
    
    return render(request, 'mlb_app/player_detail.html', context)


@require_http_methods(["GET", "POST"])
def player_stats(request, player_id):
    """
    球員統計數據視圖
    
    這個視圖提供詳細的球員統計數據查詢功能。
    使用者可以選擇不同的統計類別、時間範圍等。
    
    URL 參數：
    - player_id: 球員的 MLB ID
    
    功能：
    - 支援多種統計類別（打擊、投球、守備）
    - 支援不同時間範圍（單季、生涯、逐年）
    - 提供數據視覺化
    - 導出功能
    """
    # 從 POST 或 GET 參數獲取查詢條件
    stat_group = request.POST.get('stat_group') or request.GET.get('stat_group', 'hitting')
    stat_type = request.POST.get('stat_type') or request.GET.get('stat_type', 'season')
    season = request.POST.get('season') or request.GET.get('season')
    
    # 如果是 season 查詢但沒有指定年份，使用當前年份
    if stat_type == 'season' and not season:
        season = str(timezone.now().year)
    
    context = {
        'player_id': player_id,
        'stat_group': stat_group,
        'stat_type': stat_type,
        'season': season,
        # page_title will be updated after fetching player_info
    }

    try:
        # 1. Fetch Full Player Info
        player_info = mlb_api.get_player_info(player_id)
        if not player_info:
            logger.warning(f"Player info not found for ID {player_id} in player_stats view.")
            raise Http404("找不到該球員的詳細資訊 (Info)")

        player_name = player_info.get('fullName', str(player_id))
        context['player_info'] = player_info
        context['player_name'] = player_name
        context['page_title'] = f'{player_name} 統計數據'

        # 2. 獲取統計數據
        stats = mlb_api.get_player_stats(player_id, stat_group, stat_type, season)
        
        # 格式化統計數據以便在模板中使用
        formatted_stats = []
        for stat_split in stats:
            formatted_split = {
                'split_info': stat_split,
                'formatted_stats': {}
            }
            
            # 格式化每個統計項目
            for key, value in stat_split.get('stat', {}).items():
                formatted_split['formatted_stats'][key] = format_stat_value(value, key)
            
            formatted_stats.append(formatted_split)
        
        context.update({
            'stats': formatted_stats,
            'raw_stats': stats,  # 保留原始數據用於圖表
            'total_splits': len(stats),
        })
        
        if stats:
            logger.info(f"載入球員 {player_id} 的 {stat_group} 統計數據，{len(stats)} 個分割")
        else:
            messages.info(request, f"沒有找到該球員的 {stat_group} 統計數據。")
            
    except MLBAPIError as e:
        logger.error(f"獲取球員統計數據時發生 API 錯誤: {str(e)}")
        messages.error(request, f"獲取統計數據時發生錯誤：{str(e)}")
        context['stats'] = []
        context['total_splits'] = 0
        
    except Exception as e:
        logger.error(f"載入球員統計數據時發生未預期錯誤: {str(e)}")
        messages.error(request, "載入統計數據時發生錯誤。")
        context['stats'] = []
        context['total_splits'] = 0
    
    return render(request, 'mlb_app/player_stats.html', context)


@require_http_methods(["GET"])
@cache_page(60 * 5)  # 快取5分鐘
def api_games_json(request):
    """
    JSON API 端點：獲取比賽資訊
    
    這個視圖提供 JSON 格式的比賽資訊，供前端 JavaScript 使用。
    使用快取來提高性能。
    
    URL 參數：
    - date: 查詢日期（YYYY-MM-DD 格式）
    
    回傳：
    - JSON 格式的比賽資訊
    """
    date_str = request.GET.get('date', timezone.now().date().strftime('%Y-%m-%d'))
    
    try:
        # 驗證日期格式
        datetime.strptime(date_str, '%Y-%m-%d')
        
        # 獲取比賽資訊
        games = mlb_api.get_games_by_date(date_str)
        
        return JsonResponse({
            'success': True,
            'date': date_str,
            'games': games,
            'total': len(games)
        })
        
    except ValueError:
        return JsonResponse({
            'success': False,
            'error': '日期格式錯誤'
        }, status=400)
        
    except MLBAPIError as e:
        logger.error(f"API 查詢比賽時發生錯誤: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
        
    except Exception as e:
        logger.error(f"API 端點發生未預期錯誤: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': '服務器內部錯誤'
        }, status=500)


@require_http_methods(["GET"])
@cache_page(60 * 10)  # 快取10分鐘
def api_player_search_json(request):
    """
    JSON API 端點：球員搜尋
    
    這個視圖提供 JSON 格式的球員搜尋結果，供自動完成功能使用。
    
    URL 參數：
    - q: 搜尋關鍵字
    - limit: 結果數量限制（預設10）
    
    回傳：
    - JSON 格式的球員資訊列表
    """
    query = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 10))
    
    if len(query) < 2:
        return JsonResponse({
            'success': False,
            'error': '搜尋關鍵字至少需要2個字符'
        }, status=400)
    
    try:
        players = mlb_api.search_player(query)
        
        # 限制結果數量
        if limit > 0:
            players = players[:limit]
        
        return JsonResponse({
            'success': True,
            'query': query,
            'players': players,
            'total': len(players)
        })
        
    except MLBAPIError as e:
        logger.error(f"API 搜尋球員時發生錯誤: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
        
    except Exception as e:
        logger.error(f"球員搜尋 API 發生未預期錯誤: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': '服務器內部錯誤'
        }, status=500)


def register_request(request):
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful." )
            return redirect("mlb_app:index") # Assuming 'index' is the name of your homepage URL
        else:
            # Construct messages for each error
            # error_message = "Unsuccessful registration. Invalid information." # General message
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")
            # messages.error(request, error_message)
    else:
        form = UserRegisterForm()
    return render(request=request, template_name="mlb_app/register.html", context={"form":form, "page_title": "用戶註冊"})


def get_client_ip(request):
    """
    獲取客戶端 IP 地址的輔助函數
    
    這個函數嘗試從 HTTP 標頭中獲取真實的客戶端 IP 地址。
    考慮了代理伺服器和負載平衡器的情況。
    
    參數：
        request: Django HTTP 請求對象
        
    回傳：
        str: 客戶端 IP 地址
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def about(request):
    """
    關於頁面視圖
    
    顯示關於這個 MLB 統計查詢系統的資訊。
    """
    context = {
        'page_title': '關於我們',
    }
    return render(request, 'mlb_app/about.html', context)


def help_page(request):
    """
    幫助頁面視圖
    
    顯示使用說明和常見問題解答。
    """
    context = {
        'page_title': '使用說明',
    }
    return render(request, 'mlb_app/help.html', context)


# 錯誤處理視圖
def handler404(request, exception):
    """
    自定義 404 錯誤頁面
    """
    return render(request, 'mlb_app/errors/404.html', {
        'page_title': '頁面未找到'
    }, status=404)


def handler500(request):
    """
    自定義 500 錯誤頁面
    """
    return render(request, 'mlb_app/errors/500.html', {
        'page_title': '服務器錯誤'
    }, status=500)
