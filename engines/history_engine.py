import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import uuid

@dataclass
class SearchRecord:
    id: str
    timestamp: str
    query_type: str  # 'text', 'image', 'filter'
    query_content: str
    results_count: int
    selected_product: Optional[str] = None
    filters_used: Optional[Dict] = None
    confidence: Optional[float] = None

class SearchHistory:
    def __init__(self, history_path: str = "./history/search_log.json"):
        self.history_path = Path(history_path)
        self.records: List[SearchRecord] = []
        self._ensure_file()
        self._load_history()
    
    def _ensure_file(self):
        """确保文件存在"""
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.history_path.exists():
            self.history_path.write_text('[]', encoding='utf-8')
    
    def _load_history(self):
        """加载历史记录"""
        try:
            with open(self.history_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.records = [SearchRecord(**record) for record in data]
        except Exception as e:
            print(f"Error loading history: {e}")
            self.records = []
    
    def _save_history(self):
        """保存历史记录"""
        try:
            data = [asdict(record) for record in self.records]
            with open(self.history_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")
    
    def add_record(self, 
                   query_type: str,
                   query_content: str,
                   results_count: int,
                   selected_product: Optional[str] = None,
                   filters_used: Optional[Dict] = None,
                   confidence: Optional[float] = None) -> str:
        """添加搜索记录"""
        record = SearchRecord(
            id=str(uuid.uuid4())[:8],
            timestamp=datetime.now().isoformat(),
            query_type=query_type,
            query_content=query_content,
            results_count=results_count,
            selected_product=selected_product,
            filters_used=filters_used,
            confidence=confidence
        )
        
        self.records.append(record)
        
        # 只保留最近100条记录（隐私保护）
        if len(self.records) > 100:
            self.records = self.records[-100:]
        
        self._save_history()
        return record.id
    
    def get_recent_searches(self, limit: int = 10) -> List[Dict]:
        """获取最近搜索"""
        recent = self.records[-limit:]
        return [asdict(r) for r in reversed(recent)]
    
    def get_statistics(self) -> Dict:
        """获取搜索统计"""
        if not self.records:
            return {}
        
        total = len(self.records)
        text_searches = len([r for r in self.records if r.query_type == 'text'])
        image_searches = len([r for r in self.records if r.query_type == 'image'])
        filter_searches = len([r for r in self.records if r.query_type == 'filter'])
        
        # 热门搜索词
        queries = [r.query_content for r in self.records if r.query_type == 'text']
        query_counts = {}
        for q in queries:
            query_counts[q] = query_counts.get(q, 0) + 1
        
        top_queries = sorted(query_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'total_searches': total,
            'text_searches': text_searches,
            'image_searches': image_searches,
            'filter_searches': filter_searches,
            'top_queries': top_queries
        }
    
    def clear_history(self):
        """清空历史（用户主动清除）"""
        self.records = []
        self._save_history()
    
    def export_history(self) -> str:
        """导出历史为JSON字符串"""
        return json.dumps([asdict(r) for r in self.records], ensure_ascii=False, indent=2)

# 全局实例
history = SearchHistory()
