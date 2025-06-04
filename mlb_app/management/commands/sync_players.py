"""
同步 MLB 球員數據的管理命令

這個命令用於從 MLB API 同步球員數據到本地資料庫。
它是一個很好的範例，展示了如何：
1. 建立自定義的 Django 管理命令
2. 整合外部 API
3. 批量處理數據
4. 錯誤處理和日誌記錄
5. 進度顯示

使用方法：
python manage.py sync_players
python manage.py sync_players --team yankees
python manage.py sync_players --force-update
python manage.py sync_players --dry-run
"""

import time
import logging
from typing import Dict, List, Any, Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.core.cache import cache

from mlb_app.models import Player, Team
from mlb_app.utils import mlb_api, MLBAPIError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    同步 MLB 球員數據的管理命令
    
    這個命令繼承自 Django 的 BaseCommand，讓我們能夠創建自定義的管理命令。
    管理命令是 Django 提供的強大功能，允許我們創建可以在命令行執行的腳本。
    """
    
    help = '同步 MLB 球員數據到本地資料庫'
    
    def add_arguments(self, parser):
        """
        定義命令行參數
        
        這個方法讓我們的命令支援各種選項和參數，提高靈活性。
        """
        # 可選參數：指定特定球隊
        parser.add_argument(
            '--team',
            type=str,
            help='只同步指定球隊的球員 (例如: yankees, dodgers)',
        )
        
        # 可選參數：強制更新
        parser.add_argument(
            '--force-update',
            action='store_true',
            help='強制更新所有球員數據，即使最近已更新過',
        )
        
        # 可選參數：乾燥運行（不實際修改數據）
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只顯示會執行的操作，不實際修改數據',
        )
        
        # 可選參數：詳細輸出
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='顯示詳細的處理過程',
        )
        
        # 可選參數：批次大小
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='每批處理的球員數量 (預設: 50)',
        )
    
    def handle(self, *args, **options):
        """
        命令的主要執行邏輯
        
        這是命令的核心方法，包含了所有的業務邏輯。
        使用良好的錯誤處理和日誌記錄確保命令的可靠性。
        """
        start_time = time.time()
        
        # 設定詳細程度
        self.verbose = options['verbose']
        self.dry_run = options['dry_run']
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 乾燥運行模式：只顯示操作，不實際修改數據')
            )
        
        try:
            # 步驟1：獲取要處理的球隊列表
            teams = self._get_teams_to_process(options.get('team'))
            
            if not teams:
                raise CommandError("找不到要處理的球隊")
            
            self.stdout.write(f"📋 準備處理 {len(teams)} 支球隊的球員數據")
            
            # 步驟2：處理每支球隊
            total_processed = 0
            total_updated = 0
            total_created = 0
            
            for team in teams:
                self.stdout.write(f"\n🏟️  處理球隊: {team.name}")
                
                try:
                    processed, updated, created = self._sync_team_players(
                        team, 
                        options['force_update'],
                        options['batch_size']
                    )
                    
                    total_processed += processed
                    total_updated += updated
                    total_created += created
                    
                    self.stdout.write(
                        f"   ✅ 完成: {processed} 位球員處理，"
                        f"{created} 位新增，{updated} 位更新"
                    )
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"   ❌ 球隊 {team.name} 處理失敗: {str(e)}")
                    )
                    logger.error(f"處理球隊 {team.name} 時發生錯誤: {str(e)}")
                    continue
            
            # 步驟3：顯示總結
            elapsed_time = time.time() - start_time
            self._show_summary(total_processed, total_created, total_updated, elapsed_time)
            
            # 步驟4：清理快取
            if not self.dry_run:
                self._clear_related_cache()
            
        except Exception as e:
            logger.error(f"同步球員數據時發生錯誤: {str(e)}")
            raise CommandError(f"命令執行失敗: {str(e)}")
    
    def _get_teams_to_process(self, team_filter: Optional[str]) -> List[Team]:
        """
        獲取要處理的球隊列表
        
        根據用戶指定的過濾條件，返回需要處理的球隊。
        """
        if team_filter:
            # 處理特定球隊
            teams = Team.objects.filter(
                name__icontains=team_filter
            )
            
            if not teams.exists():
                # 嘗試按縮寫查找
                teams = Team.objects.filter(
                    abbreviation__iexact=team_filter
                )
            
            if not teams.exists():
                self.stdout.write(
                    self.style.WARNING(f"找不到球隊 '{team_filter}'，將處理所有球隊")
                )
                teams = Team.objects.all()
        else:
            # 處理所有球隊
            teams = Team.objects.all()
        
        return list(teams)
    
    def _sync_team_players(self, team: Team, force_update: bool, batch_size: int) -> tuple:
        """
        同步特定球隊的球員數據
        
        這個方法處理單一球隊的所有球員，包括：
        1. 從 API 獲取球員列表
        2. 批量處理球員數據
        3. 更新或創建球員記錄
        
        返回：(處理數量, 更新數量, 創建數量)
        """
        processed_count = 0
        updated_count = 0
        created_count = 0
        
        try:
            # 從 API 獲取球隊花名冊
            roster_data = self._get_team_roster(team)
            
            if not roster_data:
                self.stdout.write(f"   ⚠️  球隊 {team.name} 沒有找到球員數據")
                return processed_count, updated_count, created_count
            
            # 批量處理球員
            for i in range(0, len(roster_data), batch_size):
                batch = roster_data[i:i + batch_size]
                
                if self.verbose:
                    self.stdout.write(
                        f"   📦 處理批次 {i // batch_size + 1}: "
                        f"{len(batch)} 位球員"
                    )
                
                batch_updated, batch_created = self._process_player_batch(
                    batch, team, force_update
                )
                
                processed_count += len(batch)
                updated_count += batch_updated
                created_count += batch_created
                
                # 避免 API 頻率限制
                time.sleep(0.1)
        
        except MLBAPIError as e:
            raise Exception(f"API 錯誤: {str(e)}")
        except Exception as e:
            raise Exception(f"處理球員數據時發生錯誤: {str(e)}")
        
        return processed_count, updated_count, created_count
    
    def _get_team_roster(self, team: Team) -> List[Dict[str, Any]]:
        """
        從 API 獲取球隊花名冊
        
        這個方法封裝了 API 調用邏輯，處理錯誤和重試。
        """
        try:
            # 這裡應該調用實際的 MLB API
            # 由於我們的 utils 中的 API 主要是搜尋功能，
            # 這裡使用一個簡化的實現
            
            # 使用熱門球員作為示例數據
            popular_players = [
                'Shohei Ohtani', 'Aaron Judge', 'Mookie Betts',
                'Fernando Tatis Jr.', 'Mike Trout', 'Ronald Acuna Jr.'
            ]
            
            roster_data = []
            for player_name in popular_players:
                try:
                    players = mlb_api.search_player(player_name)
                    if players:
                        roster_data.extend(players[:1])  # 只取第一個結果
                except:
                    continue
            
            return roster_data
            
        except Exception as e:
            logger.error(f"獲取球隊 {team.name} 花名冊時發生錯誤: {str(e)}")
            return []
    
    def _process_player_batch(self, player_batch: List[Dict], team: Team, force_update: bool) -> tuple:
        """
        處理一批球員數據
        
        使用資料庫事務確保數據一致性。
        
        返回：(更新數量, 創建數量)
        """
        updated_count = 0
        created_count = 0
        
        if self.dry_run:
            # 乾燥運行模式，只計算但不實際操作
            for player_data in player_batch:
                player_id = player_data.get('id')
                if player_id:
                    exists = Player.objects.filter(mlb_id=player_id).exists()
                    if exists:
                        updated_count += 1
                    else:
                        created_count += 1
            return updated_count, created_count
        
        try:
            with transaction.atomic():
                for player_data in player_batch:
                    try:
                        updated, created = self._sync_single_player(
                            player_data, team, force_update
                        )
                        
                        if updated:
                            updated_count += 1
                        if created:
                            created_count += 1
                            
                    except Exception as e:
                        logger.warning(
                            f"處理球員 {player_data.get('fullName', 'Unknown')} "
                            f"時發生錯誤: {str(e)}"
                        )
                        continue
        
        except Exception as e:
            logger.error(f"處理球員批次時發生錯誤: {str(e)}")
            raise
        
        return updated_count, created_count
    
    def _sync_single_player(self, player_data: Dict, team: Team, force_update: bool) -> tuple:
        """
        同步單一球員數據
        
        返回：(是否更新, 是否創建)
        """
        mlb_id = player_data.get('id')
        if not mlb_id:
            return False, False
        
        # 檢查球員是否已存在
        try:
            player = Player.objects.get(mlb_id=mlb_id)
            
            # 檢查是否需要更新
            if not force_update:
                # 如果最近已更新過，跳過
                if (timezone.now() - player.updated_at).hours < 24:
                    return False, False
            
            # 更新球員資訊
            self._update_player_from_data(player, player_data, team)
            player.save()
            
            if self.verbose:
                self.stdout.write(f"     ✏️  更新球員: {player.full_name}")
            
            return True, False
            
        except Player.DoesNotExist:
            # 創建新球員
            player = self._create_player_from_data(player_data, team)
            
            if self.verbose:
                self.stdout.write(f"     ➕ 新增球員: {player.full_name}")
            
            return False, True
    
    def _update_player_from_data(self, player: Player, data: Dict, team: Team):
        """從 API 數據更新球員資訊"""
        player.full_name = data.get('fullName', player.full_name)
        player.current_team = team
        player.primary_position = data.get('primaryPosition', {}).get('abbreviation', player.primary_position)
        player.birth_date = data.get('birthDate', player.birth_date)
        
        # 解析身高體重
        if data.get('height'):
            try:
                player.height_cm = self._parse_height(data['height'])
            except:
                pass
        
        if data.get('weight'):
            try:
                player.weight_kg = self._parse_weight(data['weight'])
            except:
                pass
    
    def _create_player_from_data(self, data: Dict, team: Team) -> Player:
        """從 API 數據創建新球員"""
        return Player.objects.create(
            mlb_id=data.get('id'),
            full_name=data.get('fullName', 'Unknown'),
            current_team=team,
            primary_position=data.get('primaryPosition', {}).get('abbreviation', 'OF'),
            birth_date=data.get('birthDate'),
            height_cm=self._parse_height(data.get('height', '180 cm')),
            weight_kg=self._parse_weight(data.get('weight', '80 kg')),
        )
    
    def _parse_height(self, height_str: str) -> int:
        """解析身高字串"""
        # 簡化的解析邏輯
        try:
            if "'" in height_str:
                parts = height_str.replace('"', '').split("'")
                feet = int(parts[0])
                inches = int(parts[1]) if len(parts) > 1 else 0
                return int(feet * 30.48 + inches * 2.54)
            else:
                return int(float(height_str.replace('cm', '').strip()))
        except:
            return 180  # 預設值
    
    def _parse_weight(self, weight_str: str) -> int:
        """解析體重字串"""
        try:
            if 'lbs' in weight_str:
                pounds = float(weight_str.replace('lbs', '').strip())
                return int(pounds * 0.453592)
            else:
                return int(float(weight_str.replace('kg', '').strip()))
        except:
            return 80  # 預設值
    
    def _show_summary(self, processed: int, created: int, updated: int, elapsed_time: float):
        """顯示執行總結"""
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS("📊 同步完成！"))
        self.stdout.write(f"⏱️  執行時間: {elapsed_time:.2f} 秒")
        self.stdout.write(f"📈 處理總數: {processed} 位球員")
        self.stdout.write(f"➕ 新增: {created} 位")
        self.stdout.write(f"✏️  更新: {updated} 位")
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING("⚠️  這是乾燥運行，未實際修改數據"))
    
    def _clear_related_cache(self):
        """清理相關快取"""
        cache_keys = [
            'mlb_popular_players',
            'mlb_teams_list',
            'ml_recommendation_model'
        ]
        
        for key in cache_keys:
            cache.delete(key)
        
        if self.verbose:
            self.stdout.write("🧹 已清理相關快取")
