import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import rapidfuzz
from rapidfuzz import fuzz, process

@dataclass
class CigarProduct:
    model_id: str
    model_name: str
    brand_id: str
    brand_name: str
    series_name: str
    length_mm: Optional[int] = None
    ring_gauge: Optional[int] = None
    type: str = ""
    price_box: Optional[int] = None
    price_unit: Optional[int] = None
    packaging: str = ""
    blend_wrapper: str = ""
    blend_binder: str = ""
    blend_filler: str = ""
    blend_notes: str = ""
    verified: bool = False
    fuzzy_blend: bool = False
    features: str = ""
    flavor: List[str] = None
    
    def __post_init__(self):
        if self.flavor is None:
            self.flavor = []
        # 标记配方是否模糊
        self.fuzzy_blend = any([
            "推测" in self.blend_notes,
            "未公开" in self.blend_wrapper,
            "未公开" in self.blend_binder,
            "未公开" in self.blend_filler
        ])

class CigarDatabase:
    def __init__(self, db_path: str = "./database/cigar_data.json"):
        self.db_path = Path(db_path)
        self.products: List[CigarProduct] = []
        self.brands: Dict[str, str] = {}  # brand_id -> brand_name
        self.search_index: Dict[str, List[str]] = {}  # keyword -> [model_ids]
        self._load_data()
        self._build_index()
    
    def _load_data(self):
        """加载JSON数据库"""
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for brand in data.get('brands', []):
                brand_id = brand['brand_id']
                brand_name = brand['brand_name']
                self.brands[brand_id] = brand_name
                
                for series in brand.get('series', []):
                    series_name = series['series_name']
                    for product in series.get('products', []):
                        blend = product.get('blend', {})
                        # 处理 blend 不是字典的情况
                        if isinstance(blend, str):
                            blend = {'notes': blend, 'wrapper': '未公开', 'binder': '未公开', 'filler': '未公开'}
                        elif not isinstance(blend, dict):
                            blend = {}
                        
                        self.products.append(CigarProduct(
                            model_id=product.get('model_id', ''),
                            model_name=product.get('model_name', ''),
                            brand_id=brand_id,
                            brand_name=brand_name,
                            series_name=series_name,
                            length_mm=product.get('length_mm'),
                            ring_gauge=product.get('ring_gauge'),
                            type=product.get('type', ''),
                            price_box=product.get('price_box'),
                            price_unit=product.get('price_unit'),
                            packaging=product.get('packaging', ''),
                            blend_wrapper=blend.get('wrapper', '未公开'),
                            blend_binder=blend.get('binder', '未公开'),
                            blend_filler=blend.get('filler', '未公开'),
                            blend_notes=blend.get('notes', ''),
                            verified=blend.get('verified', False),
                            features=product.get('features', ''),
                            flavor=product.get('flavor', [])
                        ))
        except Exception as e:
            print(f"Error loading database: {e}")
    
    def _build_index(self):
        """构建搜索索引"""
        for product in self.products:
            # 提取所有关键词
            keywords = [
                product.brand_name,
                product.series_name,
                product.model_name,
                product.model_id,
                product.type,
            ]
            # 添加别名匹配
            if '揽胜' in product.model_name:
                keywords.append('lanzheng')
            if '逍遥' in product.model_name:
                keywords.append('xiaoyao')
            
            for kw in keywords:
                if kw:
                    kw_lower = kw.lower()
                    if kw_lower not in self.search_index:
                        self.search_index[kw_lower] = []
                    self.search_index[kw_lower].append(product.model_id)
    
    def search_fuzzy(self, query: str, limit: int = 10) -> List[Dict]:
        """模糊搜索"""
        results = []
        query_lower = query.lower()
        
        # 1. 精确匹配型号ID
        for p in self.products:
            if query_lower in p.model_id.lower() or query_lower in p.model_name.lower():
                results.append({
                    'product': p,
                    'score': 100,
                    'match_type': 'exact'
                })
        
        # 2. 模糊匹配
        all_names = [f"{p.brand_name} {p.series_name} {p.model_name}" for p in self.products]
        fuzzy_results = process.extract(query, all_names, scorer=fuzz.WRatio, limit=limit)
        
        for name, score, idx in fuzzy_results:
            if score > 60:
                product = self.products[idx]
                # 避免重复
                if not any(r['product'].model_id == product.model_id for r in results):
                    results.append({
                        'product': product,
                        'score': score,
                        'match_type': 'fuzzy'
                    })
        
        # 排序并返回
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]
    
    def filter_by_criteria(self, 
                          brand: Optional[str] = None,
                          wrapper: Optional[str] = None,
                          binder: Optional[str] = None,
                          filler: Optional[str] = None,
                          cigar_type: Optional[str] = None) -> List[CigarProduct]:
        """交叉筛选"""
        results = self.products
        
        if brand and brand != "all":
            results = [p for p in results if p.brand_id == brand or p.brand_name == brand]
        
        if wrapper and wrapper != "all":
            results = [p for p in results if wrapper in p.blend_wrapper]
        
        if binder and binder != "all":
            results = [p for p in results if binder in p.blend_binder]
        
        if filler and filler != "all":
            results = [p for p in results if filler in p.blend_filler]
        
        if cigar_type and cigar_type != "all":
            results = [p for p in results if cigar_type in p.type]
        
        return results
    
    def get_product_by_id(self, model_id: str) -> Optional[CigarProduct]:
        """通过ID获取产品"""
        for p in self.products:
            if p.model_id == model_id:
                return p
        return None
    
    def get_all_brands(self) -> List[Dict]:
        """获取所有品牌"""
        return [{'id': k, 'name': v} for k, v in self.brands.items()]
    
    def get_all_origins(self) -> Dict[str, List[str]]:
        """获取所有产地选项"""
        origins = {
            'wrapper': set(),
            'binder': set(),
            'filler': set()
        }
        for p in self.products:
            if p.blend_wrapper and p.blend_wrapper != "未公开":
                origins['wrapper'].add(p.blend_wrapper)
            if p.blend_binder and p.blend_binder != "未公开":
                origins['binder'].add(p.blend_binder)
            if p.blend_filler and p.blend_filler != "未公开":
                origins['filler'].add(p.blend_filler)
        
        return {k: list(v) for k, v in origins.items()}

# 全局数据库实例
db = CigarDatabase()
