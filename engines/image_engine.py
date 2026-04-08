import torch
import torch.nn as nn
from torchvision import transforms, models
from PIL import Image
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
import json

class CigarImageRecognizer:
    def __init__(self, model_path: str = None):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.image_size = 224
        
        # 使用预训练的EfficientNet
        self.model = models.efficientnet_b0(pretrained=True)
        
        # 修改分类头
        num_features = self.model.classifier[1].in_features
        self.model.classifier = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(num_features, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 182)  # 182个雪茄产品类别
        )
        
        self.model = self.model.to(self.device)
        self.model.eval()
        
        # 图像预处理
        self.transform = transforms.Compose([
            transforms.Resize((self.image_size, self.image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                               std=[0.229, 0.224, 0.225])
        ])
        
        # 特征数据库（模拟预计算的特征向量）
        self.feature_db = self._build_feature_database()
        
    def _build_feature_database(self) -> Dict:
        """构建特征数据库"""
        # 这里应该加载预计算的特征
        # 为了演示，我们返回一个简化的结构
        return {
            'size_profiles': self._build_size_profiles(),
            'color_profiles': self._build_color_profiles()
        }
    
    def _build_size_profiles(self) -> Dict:
        """构建尺寸特征库"""
        from database.cigar_db import db
        profiles = {}
        for p in db.products:
            if p.length_mm and p.ring_gauge:
                profiles[p.model_id] = {
                    'length': p.length_mm,
                    'ring': p.ring_gauge,
                    'ratio': p.length_mm / p.ring_gauge if p.ring_gauge > 0 else 0
                }
        return profiles
    
    def _build_color_profiles(self) -> Dict:
        """构建颜色特征库"""
        # 雪茄颜色等级
        color_map = {
            '浅色': [180, 160, 140],
            '中棕': [139, 119, 101],
            '深棕': [101, 67, 33],
            '马杜罗': [60, 40, 20]
        }
        return color_map
    
    def extract_features(self, image: Image.Image) -> Dict:
        """提取图像特征"""
        # 转换为RGB
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        img_array = np.array(image)
        
        # 1. 尺寸特征（通过参考物估算）
        size_features = self._estimate_size(img_array)
        
        # 2. 颜色特征
        color_features = self._analyze_color(img_array)
        
        # 3. 形状特征
        shape_features = self._analyze_shape(img_array)
        
        return {
            'size': size_features,
            'color': color_features,
            'shape': shape_features
        }
    
    def _estimate_size(self, img_array: np.ndarray) -> Dict:
        """估算尺寸"""
        h, w = img_array.shape[:2]
        aspect_ratio = h / w if w > 0 else 1
        
        # 简化的尺寸估算
        return {
            'aspect_ratio': aspect_ratio,
            'estimated_length': None,  # 需要参考物才能估算
            'estimated_ring': None
        }
    
    def _analyze_color(self, img_array: np.ndarray) -> Dict:
        """分析颜色"""
        # 提取中心区域（通常是茄衣）
        h, w = img_array.shape[:2]
        center_crop = img_array[h//4:3*h//4, w//4:3*w//4]
        
        # 计算平均颜色
        mean_color = np.mean(center_crop, axis=(0, 1))
        
        # 判断颜色等级
        color_levels = self._build_color_profiles()
        distances = {}
        for level, ref_color in color_levels.items():
            dist = np.linalg.norm(mean_color - np.array(ref_color))
            distances[level] = dist
        
        closest_color = min(distances, key=distances.get)
        
        return {
            'mean_rgb': mean_color.tolist(),
            'color_level': closest_color,
            'brightness': np.mean(mean_color)
        }
    
    def _analyze_shape(self, img_array: np.ndarray) -> Dict:
        """分析形状"""
        import cv2
        
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            largest = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest)
            
            # 判断形状类型
            shape_type = self._classify_shape(w, h)
            
            return {
                'width': w,
                'height': h,
                'shape_type': shape_type,
                'tapered': shape_type in ['鱼雷', '金字塔']
            }
        
        return {'shape_type': '未知'}
    
    def _classify_shape(self, w: int, h: int) -> str:
        """分类形状"""
        ratio = h / w if w > 0 else 1
        
        if ratio > 5:
            return '长皇冠'
        elif ratio > 3:
            return '罗布图'
        elif ratio > 2:
            return '皇冠'
        else:
            return '短支'
    
    def recognize(self, image: Image.Image, top_k: int = 5) -> List[Dict]:
        """识别雪茄"""
        from database.cigar_db import db
        
        features = self.extract_features(image)
        
        matches = []
        for product in db.products:
            score = 0
            reasons = []
            
            # 1. 尺寸匹配
            if product.length_mm and product.ring_gauge:
                size_profile = self.feature_db['size_profiles'].get(product.model_id)
                if size_profile:
                    # 尺寸匹配分数
                    score += 20
                    reasons.append(f"尺寸: {product.length_mm}mm x {product.ring_gauge}环")
            
            # 2. 颜色匹配
            color_map = {
                '多米尼加': '中棕',
                '厄瓜多尔': '浅棕',
                '巴西': '深棕',
                '尼加拉瓜': '马杜罗'
            }
            expected_color = None
            for origin, color in color_map.items():
                if origin in product.blend_wrapper:
                    expected_color = color
                    break
            
            if expected_color and features['color']['color_level'] == expected_color:
                score += 30
                reasons.append(f"颜色匹配: {expected_color}")
            
            # 3. 基础分数
            score += 10
            
            # 4. 配方完整度加分
            if product.verified:
                score += 10
            
            matches.append({
                'product': product,
                'score': min(score, 100),
                'confidence': self._calculate_confidence(score),
                'reasons': reasons,
                'features': features
            })
        
        # 排序并返回TopK
        matches.sort(key=lambda x: x['score'], reverse=True)
        return matches[:top_k]
    
    def _calculate_confidence(self, score: int) -> str:
        """计算置信度等级"""
        if score >= 90:
            return '确定匹配'
        elif score >= 70:
            return '高概率匹配'
        elif score >= 50:
            return '可能匹配'
        else:
            return '无法确定'

# 全局实例
recognizer = CigarImageRecognizer()
