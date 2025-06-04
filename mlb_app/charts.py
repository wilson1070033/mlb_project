"""
互動式圖表生成器

這個模組負責生成各種互動式統計圖表，讓使用者能夠以視覺化的方式探索 MLB 數據。
資料視覺化是資料科學的重要組成部分，它將抽象的數字轉化為直觀的視覺資訊。

視覺化的重要性：
1. 認知負荷減輕：圖表比表格更容易理解
2. 模式識別：視覺化能幫助發現數據中的趨勢和異常
3. 互動式探索：使用者可以動態調整參數來探索數據
4. 說服力：視覺化的數據更有說服力

現代網頁中常用的圖表類型：
- 折線圖：展示趨勢變化
- 柱狀圖：比較不同類別的數值
- 散點圖：探索變數之間的關係
- 熱力圖：展示二維數據的密度分佈
- 雷達圖：多維度能力比較
"""

from typing import Dict, List, Any, Optional
import json
import logging
from datetime import datetime, timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)

class ChartDataProcessor:
    """
    圖表數據處理器
    
    這個類別負責將原始的棒球統計數據轉換為圖表庫可以使用的格式。
    數據預處理是資料視覺化的關鍵步驟，決定了最終圖表的品質。
    
    數據處理的核心原則：
    1. 數據清理：移除無效或異常的數據點
    2. 標準化：確保不同來源的數據格式一致
    3. 聚合：將細粒度數據聚合為適合視覺化的層級
    4. 插值：處理缺失數據點
    """
    
    @staticmethod
    def prepare_batting_trend_data(stats_data: List[Dict], metric: str = 'avg') -> Dict[str, Any]:
        """
        準備打擊趨勢圖數據
        
        這個方法將球員歷年的打擊統計數據轉換為時間序列圖表格式。
        時間序列分析是了解球員表現變化的重要工具。
        
        參數:
            stats_data: 球員統計數據列表
            metric: 要分析的指標（avg, homeRuns, rbi 等）
            
        回傳:
            Dict: 適合圖表渲染的數據結構
        """
        try:
            # 按年份排序數據
            sorted_data = sorted(stats_data, key=lambda x: x.get('season', '2020'))
            
            years = []
            values = []
            tooltips = []
            
            for stat in sorted_data:
                season = stat.get('season', '未知')
                stat_obj = stat.get('stat', {})
                
                # 獲取指標值
                value = stat_obj.get(metric, 0)
                
                # 確保數值型態正確
                try:
                    if isinstance(value, str):
                        value = float(value) if value else 0
                    elif value is None:
                        value = 0
                except (ValueError, TypeError):
                    value = 0
                
                years.append(season)
                values.append(value)
                
                # 創建詳細的工具提示資訊
                tooltip_info = {
                    'season': season,
                    'value': value,
                    'games': stat_obj.get('gamesPlayed', 'N/A'),
                    'team': stat.get('team', {}).get('name', '未知球隊')
                }
                tooltips.append(tooltip_info)
            
            return {
                'type': 'line',
                'data': {
                    'labels': years,
                    'datasets': [{
                        'label': _get_metric_label(metric),
                        'data': values,
                        'borderColor': 'rgb(59, 130, 246)',
                        'backgroundColor': 'rgba(59, 130, 246, 0.1)',
                        'borderWidth': 3,
                        'pointRadius': 6,
                        'pointHoverRadius': 8,
                        'tension': 0.4,
                        'fill': True
                    }]
                },
                'options': {
                    'responsive': True,
                    'interaction': {
                        'intersect': False,
                        'mode': 'index'
                    },
                    'plugins': {
                        'title': {
                            'display': True,
                            'text': f'{_get_metric_label(metric)} 歷年變化趨勢'
                        },
                        'legend': {
                            'display': True,
                            'position': 'top'
                        }
                    },
                    'scales': {
                        'x': {
                            'title': {
                                'display': True,
                                'text': '年份'
                            }
                        },
                        'y': {
                            'title': {
                                'display': True,
                                'text': _get_metric_label(metric)
                            },
                            'beginAtZero': _should_begin_at_zero(metric)
                        }
                    }
                },
                'tooltips': tooltips
            }
            
        except Exception as e:
            logger.error(f"準備打擊趨勢數據時發生錯誤: {str(e)}")
            return _get_empty_chart_data('準備數據時發生錯誤')
    
    @staticmethod
    def prepare_player_comparison_data(players_data: List[Dict], metrics: List[str]) -> Dict[str, Any]:
        """
        準備球員比較雷達圖數據
        
        雷達圖非常適合展示多維度的能力比較，讓使用者能夠快速了解不同球員的優勢和劣勢。
        
        參數:
            players_data: 多個球員的數據
            metrics: 要比較的指標列表
            
        回傳:
            Dict: 雷達圖數據結構
        """
        try:
            if not players_data or not metrics:
                return _get_empty_chart_data('沒有可比較的數據')
            
            # 準備標籤（指標名稱）
            labels = [_get_metric_label(metric) for metric in metrics]
            
            # 為每個球員準備數據集
            datasets = []
            colors = ['rgb(59, 130, 246)', 'rgb(239, 68, 68)', 'rgb(34, 197, 94)', 
                     'rgb(251, 191, 36)', 'rgb(168, 85, 247)']
            
            for i, player_data in enumerate(players_data[:5]):  # 最多比較5個球員
                player_name = player_data.get('player_info', {}).get('fullName', f'球員 {i+1}')
                stats = player_data.get('stats', {})
                
                # 提取各項指標數值
                values = []
                for metric in metrics:
                    value = stats.get(metric, 0)
                    try:
                        # 標準化數值到 0-100 的範圍
                        normalized_value = _normalize_metric_value(metric, float(value))
                        values.append(normalized_value)
                    except (ValueError, TypeError):
                        values.append(0)
                
                dataset = {
                    'label': player_name,
                    'data': values,
                    'borderColor': colors[i % len(colors)],
                    'backgroundColor': colors[i % len(colors)].replace('rgb', 'rgba').replace(')', ', 0.2)'),
                    'borderWidth': 2,
                    'pointRadius': 4,
                    'pointHoverRadius': 6
                }
                datasets.append(dataset)
            
            return {
                'type': 'radar',
                'data': {
                    'labels': labels,
                    'datasets': datasets
                },
                'options': {
                    'responsive': True,
                    'plugins': {
                        'title': {
                            'display': True,
                            'text': '球員能力比較雷達圖'
                        },
                        'legend': {
                            'display': True,
                            'position': 'top'
                        }
                    },
                    'scales': {
                        'r': {
                            'beginAtZero': True,
                            'max': 100,
                            'ticks': {
                                'stepSize': 20
                            }
                        }
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"準備球員比較數據時發生錯誤: {str(e)}")
            return _get_empty_chart_data('準備比較數據時發生錯誤')
    
    @staticmethod
    def prepare_team_performance_heatmap(team_stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        準備球隊表現熱力圖數據
        
        熱力圖能夠有效展示二維數據的分佈情況，例如球隊在不同月份的表現。
        
        參數:
            team_stats: 球隊統計數據
            
        回傳:
            Dict: 熱力圖數據結構
        """
        try:
            # 模擬月份 vs 統計指標的熱力圖數據
            months = ['一月', '二月', '三月', '四月', '五月', '六月', 
                     '七月', '八月', '九月', '十月', '十一月', '十二月']
            metrics = ['勝率', '得分', '防禦率', '打擊率', '上壘率']
            
            # 生成示例數據（實際應用中應該使用真實的比賽數據）
            heatmap_data = []
            for month_idx, month in enumerate(months):
                for metric_idx, metric in enumerate(metrics):
                    # 使用簡單的算法生成示例數值
                    base_value = 50 + (month_idx % 3) * 10 + (metric_idx % 2) * 15
                    variation = (month_idx * metric_idx) % 30
                    value = min(100, max(0, base_value + variation))
                    
                    heatmap_data.append({
                        'x': month,
                        'y': metric,
                        'v': value
                    })
            
            return {
                'type': 'heatmap',
                'data': heatmap_data,
                'options': {
                    'responsive': True,
                    'plugins': {
                        'title': {
                            'display': True,
                            'text': '球隊月度表現熱力圖'
                        }
                    },
                    'scales': {
                        'x': {
                            'title': {
                                'display': True,
                                'text': '月份'
                            }
                        },
                        'y': {
                            'title': {
                                'display': True,
                                'text': '表現指標'
                            }
                        }
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"準備熱力圖數據時發生錯誤: {str(e)}")
            return _get_empty_chart_data('準備熱力圖數據時發生錯誤')
    
    @staticmethod
    def prepare_league_distribution_data(players_data: List[Dict], metric: str) -> Dict[str, Any]:
        """
        準備聯盟分佈直方圖數據
        
        直方圖能夠展示某個統計指標在聯盟中的分佈情況，幫助使用者了解球員相對於聯盟平均的表現。
        
        參數:
            players_data: 球員數據列表
            metric: 要分析的統計指標
            
        回傳:
            Dict: 直方圖數據結構
        """
        try:
            if not players_data:
                return _get_empty_chart_data('沒有可用的球員數據')
            
            # 提取所有球員的指標數值
            values = []
            for player in players_data:
                stats = player.get('stats', {})
                value = stats.get(metric, 0)
                try:
                    if isinstance(value, str):
                        value = float(value) if value else 0
                    elif value is None:
                        value = 0
                    values.append(value)
                except (ValueError, TypeError):
                    continue
            
            if not values:
                return _get_empty_chart_data('沒有有效的數值數據')
            
            # 計算直方圖的分組
            min_val = min(values)
            max_val = max(values)
            bins = 10  # 分成10組
            bin_width = (max_val - min_val) / bins
            
            histogram_data = []
            bin_labels = []
            
            for i in range(bins):
                bin_start = min_val + i * bin_width
                bin_end = min_val + (i + 1) * bin_width
                
                # 計算落在此區間的球員數量
                count = sum(1 for v in values if bin_start <= v < bin_end)
                if i == bins - 1:  # 最後一組包含最大值
                    count = sum(1 for v in values if bin_start <= v <= bin_end)
                
                histogram_data.append(count)
                bin_labels.append(f'{bin_start:.2f}-{bin_end:.2f}')
            
            return {
                'type': 'bar',
                'data': {
                    'labels': bin_labels,
                    'datasets': [{
                        'label': f'{_get_metric_label(metric)} 分佈',
                        'data': histogram_data,
                        'backgroundColor': 'rgba(59, 130, 246, 0.6)',
                        'borderColor': 'rgb(59, 130, 246)',
                        'borderWidth': 1
                    }]
                },
                'options': {
                    'responsive': True,
                    'plugins': {
                        'title': {
                            'display': True,
                            'text': f'{_get_metric_label(metric)} 聯盟分佈'
                        }
                    },
                    'scales': {
                        'x': {
                            'title': {
                                'display': True,
                                'text': f'{_get_metric_label(metric)} 區間'
                            }
                        },
                        'y': {
                            'title': {
                                'display': True,
                                'text': '球員數量'
                            },
                            'beginAtZero': True
                        }
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"準備分佈數據時發生錯誤: {str(e)}")
            return _get_empty_chart_data('準備分佈數據時發生錯誤')


# 輔助函數

def _get_metric_label(metric: str) -> str:
    """將英文指標名稱轉換為中文標籤"""
    metric_labels = {
        'avg': '打擊率',
        'homeRuns': '全壘打',
        'rbi': '打點',
        'runs': '得分',
        'hits': '安打',
        'era': '防禦率',
        'strikeOuts': '三振',
        'wins': '勝場',
        'saves': '救援',
        'whip': 'WHIP',
        'obp': '上壘率',
        'slg': '長打率',
        'ops': 'OPS',
        'fielding': '守備率'
    }
    return metric_labels.get(metric, metric.upper())

def _should_begin_at_zero(metric: str) -> bool:
    """判斷Y軸是否應該從0開始"""
    # 比率類型的指標通常不從0開始，計數類型的指標從0開始
    ratio_metrics = ['avg', 'era', 'whip', 'obp', 'slg', 'ops', 'fielding']
    return metric not in ratio_metrics

def _normalize_metric_value(metric: str, value: float) -> float:
    """將指標數值標準化到0-100的範圍"""
    # 這裡使用簡化的標準化方法，實際應用中應該基於聯盟統計來標準化
    normalization_ranges = {
        'avg': (0.200, 0.400),      # 打擊率範圍
        'homeRuns': (0, 60),        # 全壘打範圍
        'rbi': (0, 150),            # 打點範圍
        'era': (1.00, 6.00),        # 防禦率範圍（注意：越低越好）
        'strikeOuts': (0, 300),     # 三振範圍
        'wins': (0, 25),            # 勝場範圍
        'obp': (0.250, 0.450),      # 上壘率範圍
        'slg': (0.300, 0.700),      # 長打率範圍
        'ops': (0.600, 1.200)       # OPS範圍
    }
    
    if metric in normalization_ranges:
        min_val, max_val = normalization_ranges[metric]
        
        # 對於防禦率，數值越低越好，需要反向計算
        if metric == 'era':
            normalized = 100 * (max_val - value) / (max_val - min_val)
        else:
            normalized = 100 * (value - min_val) / (max_val - min_val)
        
        return max(0, min(100, normalized))
    else:
        # 如果沒有定義範圍，使用簡單的縮放
        return min(100, max(0, value * 10))

def _get_empty_chart_data(error_message: str) -> Dict[str, Any]:
    """返回空的圖表數據結構"""
    return {
        'type': 'bar',
        'data': {
            'labels': ['無數據'],
            'datasets': [{
                'label': '錯誤',
                'data': [0],
                'backgroundColor': 'rgba(239, 68, 68, 0.6)'
            }]
        },
        'options': {
            'responsive': True,
            'plugins': {
                'title': {
                    'display': True,
                    'text': error_message
                }
            }
        }
    }


class InteractiveChartBuilder:
    """
    互動式圖表建構器
    
    這個類別提供了一個統一的介面來建立各種互動式圖表。
    它封裝了複雜的圖表配置邏輯，讓其他程式模組能夠輕鬆生成圖表。
    """
    
    def __init__(self):
        self.data_processor = ChartDataProcessor()
    
    def build_batting_trend_chart(self, player_stats: List[Dict], metric: str = 'avg') -> str:
        """
        建立打擊趨勢圖表
        
        回傳 JSON 字串，可直接在前端使用 Chart.js 渲染
        """
        chart_data = self.data_processor.prepare_batting_trend_data(player_stats, metric)
        return json.dumps(chart_data, ensure_ascii=False)
    
    def build_player_comparison_chart(self, players_data: List[Dict], 
                                    metrics: List[str] = None) -> str:
        """建立球員比較雷達圖"""
        if metrics is None:
            metrics = ['avg', 'homeRuns', 'rbi', 'obp', 'slg']
        
        chart_data = self.data_processor.prepare_player_comparison_data(players_data, metrics)
        return json.dumps(chart_data, ensure_ascii=False)
    
    def build_league_distribution_chart(self, players_data: List[Dict], metric: str) -> str:
        """建立聯盟分佈直方圖"""
        chart_data = self.data_processor.prepare_league_distribution_data(players_data, metric)
        return json.dumps(chart_data, ensure_ascii=False)
    
    def build_team_heatmap(self, team_stats: Dict[str, Any]) -> str:
        """建立球隊表現熱力圖"""
        chart_data = self.data_processor.prepare_team_performance_heatmap(team_stats)
        return json.dumps(chart_data, ensure_ascii=False)


# 建立全域實例
chart_builder = InteractiveChartBuilder()
