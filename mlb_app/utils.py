"""
MLB API 工具模組

這個模組包含了所有與 MLB Stats API 互動的功能函數。
它就像是我們的 MLB 數據獲取工具箱，提供了各種用來：
- 獲取比賽資訊
- 搜尋球員資料
- 查詢統計數據
- 處理和格式化數據

的專用工具。

這個模組的設計理念是將複雜的 API 操作封裝成簡單易用的函數，
讓 Django 視圖能夠輕鬆地獲取所需的數據，而不需要關心 API 的具體細節。

使用方式：
    from .utils import mlb_api
    
    # 獲取特定日期的比賽
    games = mlb_api.get_games_by_date('2024-04-09')
    
    # 搜尋球員
    players = mlb_api.search_player('Shohei Ohtani')
"""

import requests
import datetime
import pytz
from datetime import datetime as dt
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
import logging

# 設定日誌記錄器，幫助我們追蹤和除錯 API 呼叫
logger = logging.getLogger(__name__)


class MLBAPIError(Exception):
    """
    自定義的 MLB API 異常類別
    
    當 API 呼叫發生錯誤時，我們會拋出這個異常。
    這讓我們能夠區分 MLB API 的錯誤和其他類型的錯誤，
    提供更精確的錯誤處理。
    """
    pass


class MLBAPIClient:
    """
    MLB API 客戶端類別
    
    這個類別封裝了所有與 MLB Stats API 的互動邏輯。
    它就像是一個專業的翻譯員，負責：
    1. 與 MLB API 服務器通訊
    2. 處理 API 回應
    3. 格式化數據
    4. 處理錯誤情況
    
    使用類別的好處是我們可以：
    - 維護 API 設定的一致性
    - 重用連接配置
    - 更好地管理錯誤處理
    - 提供清晰的介面
    """
    
    def __init__(self):
        """
        初始化 API 客戶端
        
        在這裡我們設定所有必要的配置，例如 API URL、超時時間等。
        這些設定來自 Django 的 settings.py 檔案，確保配置的一致性。
        """
        self.base_url = getattr(settings, 'MLB_API_BASE_URL', 'https://statsapi.mlb.com/api/v1')
        self.timeout = getattr(settings, 'MLB_API_TIMEOUT', 15)
        self.user_agent = getattr(settings, 'MLB_USER_AGENT', 
                                 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        self.local_timezone = pytz.timezone(getattr(settings, 'MLB_LOCAL_TIMEZONE', 'Asia/Taipei'))
        
        # 設定 HTTP 請求的標頭
        self.headers = {
            'User-Agent': self.user_agent,
            'Accept': 'application/json',
        }
    
    def _make_request(self, endpoint, params=None):
        """
        發送 API 請求的內部方法
        
        這是一個私有方法（以底線開頭），專門負責處理 HTTP 請求的細節。
        它包含了錯誤處理、重試邏輯和回應驗證。
        
        參數:
            endpoint (str): API 端點路徑
            params (dict): URL 參數
            
        回傳:
            dict: 解析後的 JSON 回應
            
        異常:
            MLBAPIError: 當 API 請求失敗時
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            logger.debug(f"正在請求 MLB API: {endpoint}")
            
            response = requests.get(
                url, 
                headers=self.headers, 
                params=params, 
                timeout=self.timeout
            )
            
            # 檢查 HTTP 狀態碼
            response.raise_for_status()
            
            # 解析 JSON 回應
            data = response.json()
            
            logger.debug(f"API 請求成功: {endpoint}")
            return data
            
        except requests.exceptions.Timeout:
            error_msg = f"API 請求超時 ({self.timeout} 秒): {endpoint}"
            logger.error(error_msg)
            raise MLBAPIError(error_msg)
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP 錯誤 {response.status_code}: {endpoint}"
            logger.error(error_msg)
            raise MLBAPIError(error_msg)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"網路請求錯誤: {str(e)}"
            logger.error(error_msg)
            raise MLBAPIError(error_msg)
            
        except ValueError as e:
            error_msg = f"API 回應格式錯誤: {str(e)}"
            logger.error(error_msg)
            raise MLBAPIError(error_msg)
    
    def get_games_by_date(self, date_str):
        """
        獲取指定日期的比賽資訊
        
        這個方法查詢特定日期的所有 MLB 比賽，返回包含比賽詳細資訊的列表。
        每場比賽的資訊包括球隊、分數、狀態、時間等。
        
        參數:
            date_str (str): 'YYYY-MM-DD' 格式的日期字串
            
        回傳:
            list: 包含比賽資訊字典的列表
            
        範例:
            games = api.get_games_by_date('2024-04-09')
            for game in games:
                print(f"{game['away_team']} vs {game['home_team']}")
        """
        # 建立快取鍵，避免重複請求相同的數據
        cache_key = f"mlb_games_{date_str}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            logger.debug(f"從快取獲取比賽數據: {date_str}")
            return cached_data
        
        # 構建 API 請求參數
        # hydrate 參數讓我們獲取更詳細的資訊
        params = {
            'sportId': 1,  # MLB 的運動 ID
            'date': date_str,
            'hydrate': 'team,linescore(matchup,runners),game(content(media(epg),summary),tickets)'
        }
        
        try:
            data = self._make_request('schedule', params)
            
            # 處理 API 回應
            games = []
            if data.get('dates'):
                for date_data in data['dates']:
                    for game_data in date_data.get('games', []):
                        # 格式化比賽資訊
                        formatted_game = self._format_game_data(game_data)
                        games.append(formatted_game)
            
            # 將結果存入快取（快取 5 分鐘）
            cache.set(cache_key, games, 300)
            
            logger.info(f"獲取到 {len(games)} 場比賽資訊: {date_str}")
            return games
            
        except MLBAPIError:
            # 重新拋出我們的自定義異常
            raise
        except Exception as e:
            error_msg = f"處理比賽數據時發生錯誤: {str(e)}"
            logger.error(error_msg)
            raise MLBAPIError(error_msg)
    
    def _format_game_data(self, game_data):
        """
        格式化比賽數據的內部方法
        
        這個方法將 MLB API 的原始比賽數據轉換成我們應用程式更容易使用的格式。
        它就像是一個數據清潔工，把雜亂的原始數據整理成整齊有用的資訊。
        
        參數:
            game_data (dict): MLB API 返回的原始比賽數據
            
        回傳:
            dict: 格式化後的比賽資訊
        """
        try:
            teams = game_data.get('teams', {})
            away_team = teams.get('away', {})
            home_team = teams.get('home', {})
            linescore = game_data.get('linescore', {})
            status = game_data.get('status', {})
            
            # 格式化比賽時間
            game_time_utc = game_data.get('gameDate', '')
            local_time_str, start_time_str = self._format_game_time(game_time_utc)
            
            # 獲取分數資訊
            away_score = self._get_team_score(away_team, linescore, 'away')
            home_score = self._get_team_score(home_team, linescore, 'home')
            
            # 格式化狀態資訊
            status_info = self._format_game_status(status, linescore, start_time_str)
            
            return {
                'game_pk': game_data.get('gamePk'),
                'game_date': game_data.get('gameDate'),
                'local_time': local_time_str,
                'start_time': start_time_str,
                'status': status_info,
                'away_team': {
                    'name': away_team.get('team', {}).get('name', 'N/A'),
                    'abbreviation': away_team.get('team', {}).get('abbreviation', 'N/A'),
                    'score': away_score
                },
                'home_team': {
                    'name': home_team.get('team', {}).get('name', 'N/A'),
                    'abbreviation': home_team.get('team', {}).get('abbreviation', 'N/A'),
                    'score': home_score
                },
                'linescore': linescore,
                'summary_url': self._get_game_summary_url(game_data)
            }
            
        except Exception as e:
            logger.error(f"格式化比賽數據時發生錯誤: {str(e)}")
            # 返回基本的比賽資訊，即使格式化失敗
            return {
                'game_pk': game_data.get('gamePk', 'N/A'),
                'status': '資料處理錯誤',
                'away_team': {'name': '未知', 'score': '-'},
                'home_team': {'name': '未知', 'score': '-'}
            }
    
    def _format_game_time(self, game_time_utc_str):
        """
        將 UTC 時間轉換為本地時間的內部方法
        
        MLB API 提供的時間是 UTC 格式，我們需要轉換成台北時間讓使用者更容易理解。
        
        參數:
            game_time_utc_str (str): UTC 時間字串
            
        回傳:
            tuple: (完整本地時間字串, 開始時間字串)
        """
        if not game_time_utc_str:
            return "時間未知", "時間未知"
        
        try:
            # 解析 UTC 時間
            game_time_utc = dt.fromisoformat(game_time_utc_str.replace('Z', '+00:00'))
            
            # 轉換到本地時區
            game_time_local = game_time_utc.astimezone(self.local_timezone)
            
            # 格式化時間字串
            full_time_str = game_time_local.strftime('%Y-%m-%d %H:%M %Z')
            start_time_str = game_time_local.strftime('%H:%M')
            
            return full_time_str, start_time_str
            
        except (ValueError, TypeError) as e:
            logger.warning(f"無法解析比賽時間 '{game_time_utc_str}': {str(e)}")
            return "時間格式錯誤", "時間格式錯誤"
    
    def _get_team_score(self, team_data, linescore, team_side):
        """
        獲取球隊分數的內部方法
        
        分數資訊可能存在於不同的地方，這個方法會嘗試從最可靠的來源獲取。
        
        參數:
            team_data (dict): 球隊資訊
            linescore (dict): 比賽計分資訊
            team_side (str): 'away' 或 'home'
            
        回傳:
            str: 格式化的分數字串
        """
        try:
            # 首先嘗試從 linescore 獲取（最準確）
            if linescore and linescore.get('teams'):
                score = linescore['teams'].get(team_side, {}).get('runs')
                if score is not None:
                    return str(score)
            
            # 其次嘗試從 team_data 獲取
            score = team_data.get('score')
            if score is not None:
                return str(score)
            
            # 如果都沒有，返回預設值
            return '-'
            
        except Exception:
            return '-'
    
    def _format_game_status(self, status, linescore, start_time_str):
        """
        格式化比賽狀態的內部方法
        
        這個方法將 MLB API 的狀態資訊轉換成更容易理解的中文描述。
        
        參數:
            status (dict): 比賽狀態資訊
            linescore (dict): 計分資訊
            start_time_str (str): 開始時間字串
            
        回傳:
            str: 格式化的狀態字串
        """
        detailed_state = status.get('detailedState', '未知狀態')
        
        # 比賽結束
        if detailed_state in ['Final', 'Game Over'] or 'Completed' in detailed_state:
            inning = linescore.get('currentInning')
            if inning and inning != 9:
                return f"終局 (F/{inning})"
            return "終局"
        
        # 比賽進行中
        elif detailed_state == 'In Progress':
            inning_ordinal = linescore.get('currentInningOrdinal', '?')
            inning_state = linescore.get('inningState', '')
            
            # 翻譯局數狀態
            if inning_state == 'Top':
                inning_state = '上'
            elif inning_state == 'Bottom':
                inning_state = '下'
            
            return f"進行中 ({inning_state}{inning_ordinal})"
        
        # 預定開始
        elif detailed_state in ['Scheduled', 'Pre-Game', 'Warmup']:
            return f"預定 {start_time_str}"
        
        # 延期
        elif 'Postponed' in detailed_state:
            return "延期"
        
        # 暫停
        elif 'Suspended' in detailed_state:
            return "暫停"
        
        # 取消
        elif 'Cancelled' in detailed_state or 'Canceled' in detailed_state:
            return "取消"
        
        # 其他狀態
        else:
            return detailed_state
    
    def _get_game_summary_url(self, game_data):
        """
        獲取比賽摘要 URL 的內部方法
        
        這個方法嘗試從比賽數據中提取摘要連結。
        
        參數:
            game_data (dict): 比賽資訊
            
        回傳:
            str: 摘要 URL 或 None
        """
        try:
            content_summary = game_data.get('content', {}).get('summary')
            
            if isinstance(content_summary, str) and content_summary.startswith('/'):
                return f"https://www.mlb.com{content_summary}"
            elif isinstance(content_summary, dict):
                url = content_summary.get('url')
                if url and url.startswith('/'):
                    return f"https://www.mlb.com{url}"
                return url
            
            return None
            
        except Exception:
            return None
    
    def search_player(self, player_name):
        """
        搜尋球員的方法
        
        這個方法根據球員姓名搜尋 MLB 球員資訊。
        它會搜尋現役球員，並返回符合條件的球員列表。
        
        參數:
            player_name (str): 球員姓名（建議使用英文全名）
            
        回傳:
            list: 包含球員資訊字典的列表
            
        範例:
            players = api.search_player('Shohei Ohtani')
            for player in players:
                print(f"{player['fullName']} - {player['currentTeam']}")
        """
        # 建立快取鍵
        cache_key = f"mlb_player_search_{player_name.lower().replace(' ', '_')}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            logger.debug(f"從快取獲取球員搜尋結果: {player_name}")
            return cached_data
        
        params = {
            'names': player_name,
            'active': 'true'  # 只搜尋現役球員
        }
        
        try:
            data = self._make_request('people/search', params)
            
            players = []
            if data.get('people'):
                for player_data in data['people']:
                    formatted_player = self._format_player_data(player_data)
                    players.append(formatted_player)
            
            # 將結果存入快取（快取 10 分鐘）
            cache.set(cache_key, players, 600)
            
            logger.info(f"找到 {len(players)} 位球員: {player_name}")
            return players
            
        except MLBAPIError:
            raise
        except Exception as e:
            error_msg = f"搜尋球員時發生錯誤: {str(e)}"
            logger.error(error_msg)
            raise MLBAPIError(error_msg)
    
    def get_player_info(self, player_id):
        """
        獲取指定球員的基本資訊

        參數:
            player_id (int): 球員的 MLB ID

        回傳:
            dict: 格式化後的球員資訊，或在找不到時返回 None
        """
        cache_key = f"mlb_player_info_{player_id}"
        cached_data = cache.get(cache_key)

        if cached_data:
            logger.debug(f"從快取獲取球員資訊: {player_id}")
            return cached_data

        try:
            # Initially, try without explicit hydrate to see if default response is sufficient
            data = self._make_request(f'people/{player_id}')

            if data.get('people') and len(data['people']) > 0:
                player_data = data['people'][0]
                formatted_player = self._format_player_data(player_data)

                # Cache for 15 minutes
                cache.set(cache_key, formatted_player, 900)
                logger.info(f"獲取並快取球員資訊: {player_id}")
                return formatted_player
            else:
                logger.warning(f"找不到 ID 為 {player_id} 的球員資訊")
                return None
        except MLBAPIError as e:
            logger.error(f"獲取球員 {player_id} 資訊時發生 API 錯誤: {str(e)}")
            raise # Re-raise the error to be handled by the caller
        except Exception as e:
            error_msg = f"處理球員 {player_id} 資訊時發生未預期錯誤: {str(e)}"
            logger.error(error_msg)
            raise MLBAPIError(error_msg)

    def _format_player_data(self, player_data):
        """
        格式化球員數據的內部方法
        
        將 MLB API 的原始球員數據轉換成我們應用程式使用的格式。
        
        參數:
            player_data (dict): MLB API 返回的原始球員數據
            
        回傳:
            dict: 格式化後的球員資訊
        """
        try:
            return {
                'id': player_data.get('id'),
                'fullName': player_data.get('fullName', 'N/A'),
                'currentTeam': player_data.get('currentTeam', {}).get('name', '自由球員'),
                'primaryPosition': player_data.get('primaryPosition', {}).get('abbreviation', 'N/A'),
                'birthDate': player_data.get('birthDate'),
                'height': player_data.get('height'),
                'weight': player_data.get('weight'),
                'batSide': player_data.get('batSide', {}).get('description', 'N/A'),
                'pitchHand': player_data.get('pitchHand', {}).get('description', 'N/A')
            }
        except Exception as e:
            logger.error(f"格式化球員數據時發生錯誤: {str(e)}")
            return {
                'id': player_data.get('id', 'N/A'),
                'fullName': player_data.get('fullName', '未知'),
                'currentTeam': '資料處理錯誤',
                'primaryPosition': 'N/A'
            }
    
    def get_player_stats(self, player_id, stat_group="hitting", stat_type="season", season=None):
        """
        獲取球員統計數據的方法
        
        這個方法查詢特定球員的各項統計數據，支援不同的統計類別和時間範圍。
        
        參數:
            player_id (int): 球員的 MLB ID
            stat_group (str): 統計類別 ('hitting', 'pitching', 'fielding')
            stat_type (str): 統計類型 ('season', 'career', 'yearByYear')
            season (str): 賽季年份 (YYYY 格式，僅在 stat_type='season' 時需要)
            
        回傳:
            list: 包含統計數據的列表
            
        範例:
            stats = api.get_player_stats(660271, 'hitting', 'season', '2024')
            for stat in stats:
                print(f"打擊率: {stat['stat']['avg']}")
        """
        current_year = dt.now().year
        if stat_type == "season" and season is None:
            season = str(current_year)
        
        # 建立快取鍵
        cache_key = f"mlb_player_stats_{player_id}_{stat_group}_{stat_type}_{season or 'none'}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            logger.debug(f"從快取獲取球員統計: {player_id}")
            return cached_data
        
        # 構建 hydrate 參數
        hydrate_parts = [f"group=[{stat_group}]", f"type=[{stat_type}]"]
        if stat_type == "season" and season:
            hydrate_parts.append(f"season={season}")
        
        hydrate_string = f"stats({','.join(hydrate_parts)})"
        
        params = {
            'hydrate': hydrate_string
        }
        
        try:
            data = self._make_request(f'people/{player_id}', params)
            
            # 提取統計數據
            stats = []
            if data.get('people') and len(data['people']) > 0:
                player_stats = data['people'][0].get('stats', [])
                if player_stats:
                    stats = player_stats[0].get('splits', [])
            
            # 將結果存入快取（快取 5 分鐘）
            cache.set(cache_key, stats, 300)
            
            logger.info(f"獲取到球員 {player_id} 的 {len(stats)} 項統計數據")
            return stats
            
        except MLBAPIError:
            raise
        except Exception as e:
            error_msg = f"獲取球員統計時發生錯誤: {str(e)}"
            logger.error(error_msg)
            raise MLBAPIError(error_msg)


# 建立全域的 API 客戶端實例
# 這樣我們在整個應用程式中都可以使用同一個配置好的客戶端
mlb_api = MLBAPIClient()


def get_today_games():
    """
    獲取今天的比賽資訊
    
    這是一個便利函數，直接返回今天的比賽列表。
    
    回傳:
        list: 今天的比賽列表
    """
    today = timezone.now().date().strftime('%Y-%m-%d')
    return mlb_api.get_games_by_date(today)


def get_popular_players():
    """
    獲取熱門球員列表
    
    這個函數可以返回一些熱門球員的資訊，用於首頁展示。
    目前返回一些知名球員，未來可以根據搜尋頻率動態調整。
    
    回傳:
        list: 熱門球員列表
    """
    popular_names = ['Shohei Ohtani', 'Aaron Judge', 'Mookie Betts', 'Fernando Tatis Jr.']
    all_players = []
    
    for name in popular_names:
        try:
            players = mlb_api.search_player(name)
            if players:
                all_players.extend(players[:1])  # 只取第一個結果
        except MLBAPIError:
            continue  # 忽略錯誤，繼續處理下一個球員
    
    return all_players


def format_stat_value(value, stat_key):
    """
    格式化統計數據值
    
    這個函數將統計數據格式化為更易讀的形式。
    例如將打擊率格式化為三位小數。
    
    參數:
        value: 統計數據值
        stat_key (str): 統計項目的鍵值
        
    回傳:
        str: 格式化後的值
    """
    if value is None or value == '':
        return '-'
    
    # 需要格式化為三位小數的統計項目
    decimal_stats = ['avg', 'obp', 'slg', 'ops', 'era', 'whip', 'fielding']
    
    if stat_key.lower() in decimal_stats:
        try:
            return f"{float(value):.3f}"
        except (ValueError, TypeError):
            return str(value)
    
    return str(value)
