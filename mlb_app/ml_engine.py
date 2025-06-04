"""
機器學習引擎模組

這個模組實作了多種機器學習演算法來提升 MLB 統計查詢系統的智慧化程度。
包含以下主要功能：

1. 協同過濾推薦系統 (Collaborative Filtering)
2. 球員表現預測模型 (Performance Prediction)
3. 異常檢測系統 (Anomaly Detection)
4. 使用者行為分析 (User Behavior Analysis)

這些 AI 技術在現代網路應用中被廣泛使用，了解其實作原理對 CS 學生非常重要。

機器學習的核心概念：
- 監督學習：從已標記的數據中學習模式
- 無監督學習：從未標記的數據中發現隱藏模式
- 推薦系統：基於使用者行為和物品特徵提供個人化建議
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
from django.core.cache import cache
from django.utils import timezone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
from sklearn.cluster import KMeans
import logging
import pickle
import json

logger = logging.getLogger(__name__)

class PlayerRecommendationEngine:
    """
    球員推薦引擎
    
    這個類別實作了基於內容的推薦系統 (Content-Based Filtering)。
    它分析球員的統計特徵，為使用者推薦相似的球員。
    
    工作原理：
    1. 特徵提取：將球員數據轉換為數值特徵向量
    2. 相似度計算：使用餘弦相似度計算球員間的相似程度
    3. 推薦生成：基於相似度分數推薦相關球員
    
    這種方法的優點是不需要大量使用者行為數據，適合新系統。
    """
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.feature_cache = {}
        self.similarity_matrix = None
        self.player_features_df = None
        
    def build_player_features(self, players_data: List[Dict]) -> pd.DataFrame:
        """
        建構球員特徵矩陣
        
        這個方法將球員的統計數據轉換為機器學習可以處理的特徵向量。
        特徵工程是機器學習中非常重要的一步。
        
        參數:
            players_data: 包含球員統計數據的字典列表
            
        回傳:
            pd.DataFrame: 標準化後的特徵矩陣
        """
        features_list = []
        
        for player in players_data:
            try:
                # 提取數值特徵
                features = {
                    'player_id': player.get('id', 0),
                    'position_code': self._encode_position(player.get('primaryPosition', 'OF')),
                    'height_cm': self._parse_height(player.get('height', '180 cm')),
                    'weight_kg': self._parse_weight(player.get('weight', '80 kg')),
                    'age': self._calculate_age(player.get('birthDate')),
                    'batting_hand': self._encode_batting_hand(player.get('batSide', 'R')),
                    'team_strength': self._get_team_strength(player.get('currentTeam', ''))
                }
                
                # 添加統計特徵（如果有的話）
                stats = player.get('stats', {})
                features.update({
                    'avg': float(stats.get('avg', 0.250)),
                    'home_runs': int(stats.get('homeRuns', 0)),
                    'rbi': int(stats.get('rbi', 0)),
                    'era': float(stats.get('era', 4.00)),
                    'strikeouts': int(stats.get('strikeOuts', 0))
                })
                
                features_list.append(features)
                
            except Exception as e:
                logger.warning(f"處理球員 {player.get('id', 'unknown')} 特徵時發生錯誤: {str(e)}")
                continue
        
        # 轉換為 DataFrame
        df = pd.DataFrame(features_list)
        
        # 標準化數值特徵
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        numeric_columns = numeric_columns.drop('player_id')  # 保留 ID 不進行標準化
        
        df[numeric_columns] = self.scaler.fit_transform(df[numeric_columns])
        
        return df
    
    def calculate_similarity_matrix(self, features_df: pd.DataFrame) -> np.ndarray:
        """
        計算球員相似度矩陣
        
        使用餘弦相似度計算每兩個球員之間的相似程度。
        餘弦相似度是推薦系統中常用的相似度度量方法。
        
        參數:
            features_df: 球員特徵矩陣
            
        回傳:
            np.ndarray: 相似度矩陣
        """
        # 移除 player_id 欄位，只保留特徵
        feature_matrix = features_df.drop('player_id', axis=1).values
        
        # 計算餘弦相似度
        similarity_matrix = cosine_similarity(feature_matrix)
        
        return similarity_matrix
    
    def recommend_similar_players(self, target_player_id: int, 
                                 top_k: int = 5) -> List[Dict[str, Any]]:
        """
        為指定球員推薦相似球員
        
        這個方法是推薦系統的核心，它找出與目標球員最相似的其他球員。
        
        參數:
            target_player_id: 目標球員的 ID
            top_k: 推薦球員數量
            
        回傳:
            List[Dict]: 推薦球員列表，包含相似度分數
        """
        if self.similarity_matrix is None or self.player_features_df is None:
            logger.error("相似度矩陣未建立，請先調用 train_model 方法")
            return []
        
        try:
            # 找到目標球員在矩陣中的索引
            target_idx = self.player_features_df[
                self.player_features_df['player_id'] == target_player_id
            ].index
            
            if len(target_idx) == 0:
                logger.warning(f"找不到球員 ID {target_player_id}")
                return []
            
            target_idx = target_idx[0]
            
            # 取得相似度分數
            similarity_scores = self.similarity_matrix[target_idx]
            
            # 排序並取得前 k 個（排除自己）
            similar_indices = np.argsort(similarity_scores)[::-1][1:top_k+1]
            
            recommendations = []
            for idx in similar_indices:
                player_id = int(self.player_features_df.iloc[idx]['player_id'])
                similarity_score = float(similarity_scores[idx])
                
                recommendations.append({
                    'player_id': player_id,
                    'similarity_score': similarity_score,
                    'recommendation_reason': self._generate_reason(target_idx, idx)
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"生成推薦時發生錯誤: {str(e)}")
            return []
    
    def train_model(self, players_data: List[Dict]):
        """
        訓練推薦模型
        
        這個方法建立特徵矩陣和相似度矩陣，是整個推薦系統的基礎。
        """
        logger.info("開始訓練球員推薦模型...")
        
        # 建構特徵矩陣
        self.player_features_df = self.build_player_features(players_data)
        
        # 計算相似度矩陣
        self.similarity_matrix = self.calculate_similarity_matrix(self.player_features_df)
        
        # 快取模型
        cache_data = {
            'features_df': self.player_features_df.to_dict(),
            'similarity_matrix': self.similarity_matrix.tolist(),
            'scaler': pickle.dumps(self.scaler)
        }
        cache.set('ml_recommendation_model', cache_data, 3600)  # 快取 1 小時
        
        logger.info(f"推薦模型訓練完成，包含 {len(self.player_features_df)} 位球員")
    
    def _encode_position(self, position: str) -> float:
        """將守備位置編碼為數值"""
        position_mapping = {
            'P': 1.0, 'C': 2.0, '1B': 3.0, '2B': 4.0, '3B': 5.0,
            'SS': 6.0, 'LF': 7.0, 'CF': 8.0, 'RF': 9.0, 'DH': 10.0,
            'OF': 7.5, 'IF': 4.5, 'UT': 5.5
        }
        return position_mapping.get(position, 5.0)
    
    def _parse_height(self, height_str: str) -> float:
        """解析身高字串並轉換為公分"""
        try:
            # 處理像 "6'2\"" 的格式
            if "'" in height_str:
                parts = height_str.replace('"', '').split("'")
                feet = int(parts[0])
                inches = int(parts[1]) if len(parts) > 1 else 0
                return feet * 30.48 + inches * 2.54
            else:
                # 處理像 "185 cm" 的格式
                return float(height_str.replace('cm', '').strip())
        except:
            return 180.0  # 預設值
    
    def _parse_weight(self, weight_str: str) -> float:
        """解析體重字串並轉換為公斤"""
        try:
            if 'lbs' in weight_str:
                pounds = float(weight_str.replace('lbs', '').strip())
                return pounds * 0.453592
            else:
                return float(weight_str.replace('kg', '').strip())
        except:
            return 80.0  # 預設值
    
    def _calculate_age(self, birth_date: str) -> float:
        """計算年齡"""
        try:
            if birth_date:
                birth = datetime.strptime(birth_date, '%Y-%m-%d')
                age = (datetime.now() - birth).days / 365.25
                return age
        except:
            pass
        return 25.0  # 預設年齡
    
    def _encode_batting_hand(self, bat_side: str) -> float:
        """編碼打擊慣用手"""
        mapping = {'L': 0.0, 'R': 1.0, 'S': 0.5, 'B': 0.5}
        return mapping.get(bat_side, 1.0)
    
    def _get_team_strength(self, team_name: str) -> float:
        """評估球隊實力（簡化版本）"""
        # 這裡可以根據球隊歷史戰績等資料來評估
        # 目前使用簡化的映射
        strong_teams = ['New York Yankees', 'Los Angeles Dodgers', 'Houston Astros']
        if team_name in strong_teams:
            return 1.0
        return 0.5
    
    def _generate_reason(self, target_idx: int, similar_idx: int) -> str:
        """生成推薦理由"""
        target_features = self.player_features_df.iloc[target_idx]
        similar_features = self.player_features_df.iloc[similar_idx]
        
        # 找出最相似的特徵
        feature_diff = abs(target_features - similar_features)
        most_similar_feature = feature_diff.drop('player_id').idxmin()
        
        reason_mapping = {
            'position_code': '守備位置相似',
            'height_cm': '身型相近',
            'age': '年齡相仿',
            'avg': '打擊率接近',
            'home_runs': '長打能力相似'
        }
        
        return reason_mapping.get(most_similar_feature, '整體特徵相似')


class PerformancePrediction:
    """
    球員表現預測系統
    
    這個類別使用機器學習預測球員未來的表現。
    它結合了歷史統計數據和球員特徵來進行預測。
    
    預測模型的基本概念：
    1. 特徵選擇：選擇對預測有幫助的特徵
    2. 模型訓練：使用歷史數據訓練預測模型
    3. 性能評估：評估模型的準確度
    4. 預測生成：對新數據進行預測
    """
    
    def __init__(self):
        self.model = None
        self.feature_scaler = StandardScaler()
        self.target_scaler = StandardScaler()
    
    def predict_batting_average(self, player_features: Dict[str, Any]) -> Tuple[float, float]:
        """
        預測球員的打擊率
        
        這個方法使用球員的歷史數據和當前特徵來預測未來的打擊率。
        
        參數:
            player_features: 球員特徵字典
            
        回傳:
            Tuple[float, float]: (預測打擊率, 信心區間)
        """
        try:
            # 特徵工程
            features = self._extract_prediction_features(player_features)
            
            # 簡化的預測邏輯（實際應用中會使用更複雜的模型）
            base_avg = features.get('career_avg', 0.250)
            age_factor = self._calculate_age_factor(features.get('age', 25))
            injury_factor = self._calculate_injury_factor(features.get('games_played', 150))
            
            predicted_avg = base_avg * age_factor * injury_factor
            
            # 計算信心區間（基於歷史變異性）
            confidence_interval = 0.05  # 簡化版本
            
            return predicted_avg, confidence_interval
            
        except Exception as e:
            logger.error(f"預測打擊率時發生錯誤: {str(e)}")
            return 0.250, 0.050  # 返回聯盟平均值
    
    def _extract_prediction_features(self, player_data: Dict) -> Dict[str, float]:
        """提取用於預測的特徵"""
        return {
            'career_avg': float(player_data.get('career_avg', 0.250)),
            'age': float(player_data.get('age', 25)),
            'games_played': float(player_data.get('games_played', 150)),
            'at_bats': float(player_data.get('at_bats', 500)),
        }
    
    def _calculate_age_factor(self, age: float) -> float:
        """計算年齡對表現的影響因子"""
        # 球員通常在27-30歲時達到巔峰
        if 27 <= age <= 30:
            return 1.0
        elif age < 27:
            return 0.9 + (age - 20) * 0.02
        else:
            return 1.0 - (age - 30) * 0.02
    
    def _calculate_injury_factor(self, games_played: float) -> float:
        """計算受傷對表現的影響因子"""
        if games_played >= 140:
            return 1.0
        else:
            return 0.8 + (games_played / 140) * 0.2


class UserBehaviorAnalyzer:
    """
    使用者行為分析系統
    
    這個類別分析使用者的搜尋模式和興趣，用於：
    1. 個人化推薦
    2. 使用者體驗優化
    3. 內容策略制定
    
    行為分析是現代數據科學的重要應用領域。
    """
    
    def __init__(self):
        self.user_profiles = {}
    
    def analyze_search_patterns(self, user_id: str, search_history: List[Dict]) -> Dict[str, Any]:
        """
        分析使用者搜尋模式
        
        這個方法分析使用者的搜尋歷史，識別興趣模式。
        
        參數:
            user_id: 使用者 ID
            search_history: 搜尋歷史列表
            
        回傳:
            Dict: 分析結果
        """
        try:
            if not search_history:
                return self._get_default_profile()
            
            # 分析搜尋頻率
            search_frequency = len(search_history)
            
            # 分析偏好的球隊
            team_searches = [s for s in search_history if s.get('search_type') == 'team']
            preferred_teams = self._extract_popular_items([s.get('search_query', '') for s in team_searches])
            
            # 分析偏好的球員位置
            player_searches = [s for s in search_history if s.get('search_type') == 'player']
            # 這裡需要額外的邏輯來分析搜尋的球員位置
            
            # 分析搜尋時間模式
            search_times = [s.get('search_time') for s in search_history if s.get('search_time')]
            peak_hours = self._analyze_time_patterns(search_times)
            
            profile = {
                'user_id': user_id,
                'search_frequency': search_frequency,
                'preferred_teams': preferred_teams,
                'peak_search_hours': peak_hours,
                'engagement_level': self._calculate_engagement_level(search_frequency),
                'recommendations': self._generate_behavior_based_recommendations(preferred_teams)
            }
            
            # 快取使用者檔案
            self.user_profiles[user_id] = profile
            
            return profile
            
        except Exception as e:
            logger.error(f"分析使用者行為時發生錯誤: {str(e)}")
            return self._get_default_profile()
    
    def _extract_popular_items(self, items: List[str]) -> List[str]:
        """提取熱門項目"""
        from collections import Counter
        counter = Counter(items)
        return [item for item, count in counter.most_common(3)]
    
    def _analyze_time_patterns(self, timestamps: List[str]) -> List[int]:
        """分析時間模式"""
        try:
            hours = []
            for ts in timestamps:
                if ts:
                    dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    hours.append(dt.hour)
            
            from collections import Counter
            hour_counts = Counter(hours)
            return [hour for hour, count in hour_counts.most_common(3)]
        except:
            return [19, 20, 21]  # 預設晚間時段
    
    def _calculate_engagement_level(self, search_frequency: int) -> str:
        """計算參與度等級"""
        if search_frequency >= 50:
            return 'high'
        elif search_frequency >= 20:
            return 'medium'
        else:
            return 'low'
    
    def _generate_behavior_based_recommendations(self, preferred_teams: List[str]) -> List[str]:
        """基於行為生成推薦"""
        recommendations = []
        
        # 基於偏好球隊推薦相關內容
        for team in preferred_teams[:2]:
            recommendations.append(f"查看 {team} 的最新比賽結果")
            recommendations.append(f"探索 {team} 的明星球員")
        
        return recommendations
    
    def _get_default_profile(self) -> Dict[str, Any]:
        """返回預設的使用者檔案"""
        return {
            'user_id': 'anonymous',
            'search_frequency': 0,
            'preferred_teams': [],
            'peak_search_hours': [19, 20, 21],
            'engagement_level': 'new',
            'recommendations': ['探索熱門球員', '查看今日比賽']
        }


# 建立全域實例
recommendation_engine = PlayerRecommendationEngine()
performance_predictor = PerformancePrediction()
behavior_analyzer = UserBehaviorAnalyzer()
