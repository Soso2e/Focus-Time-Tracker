"""
Glue機能(隙間時間の自動結合)モジュール
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any

from ..data.database import Database
from ..utils.config import get_config


class GlueEngine:
    """Glue機能クラス"""
    
    def __init__(self, db: Database):
        """
        Args:
            db: データベースインスタンス
        """
        self.db = db
        self.config = get_config()
    
    def apply_glue_rules(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Glueルールを適用してイベントを結合
        
        制作系カテゴリ → Browser(短時間) → 制作系カテゴリ のパターンを検出し、
        Browser部分を制作系として再分類
        
        Args:
            events: イベントリスト
        
        Returns:
            Glue適用後のイベントリスト
        """
        if len(events) < 3:
            return events
        
        glue_tolerance = self.config.get("glue_tolerance", 180)  # 秒
        
        # 制作系カテゴリのIDを取得
        productive_category_ids = self._get_productive_category_ids()
        
        # 調べ物カテゴリのIDを取得
        browser_category = self.db.get_category_by_name("調べ物")
        browser_category_id = browser_category["id"] if browser_category else None
        
        modified_events = []
        i = 0
        
        while i < len(events):
            current = events[i]
            
            # 3つ以上のイベントが残っている場合のみGlueチェック
            if i + 2 < len(events):
                prev_event = current
                middle_event = events[i + 1]
                next_event = events[i + 2]
                
                # Glue条件チェック
                if self._should_glue(
                    prev_event, middle_event, next_event,
                    productive_category_ids, browser_category_id,
                    glue_tolerance
                ):
                    # Browser部分を前のカテゴリに結合
                    middle_event_copy = middle_event.copy()
                    middle_event_copy["category_id"] = prev_event["category_id"]
                    middle_event_copy["is_glued"] = True
                    
                    # データベースも更新
                    self.db.update_event_category(middle_event["id"], prev_event["category_id"])
                    
                    modified_events.append(prev_event)
                    modified_events.append(middle_event_copy)
                    i += 2
                    continue
            
            modified_events.append(current)
            i += 1
        
        return modified_events
    
    def _get_productive_category_ids(self) -> List[int]:
        """制作系カテゴリのIDリストを取得"""
        categories = self.db.get_all_categories()
        return [cat["id"] for cat in categories if cat.get("is_productive", False)]
    
    def _should_glue(
        self,
        prev_event: Dict[str, Any],
        middle_event: Dict[str, Any],
        next_event: Dict[str, Any],
        productive_category_ids: List[int],
        browser_category_id: int,
        glue_tolerance: int
    ) -> bool:
        """
        Glue適用すべきかを判定
        
        条件:
        1. 前のイベントが制作系
        2. 中間のイベントが調べ物(Browser)
        3. 次のイベントが制作系
        4. 中間のイベントの長さがglue_tolerance以内
        
        Args:
            prev_event: 前のイベント
            middle_event: 中間のイベント
            next_event: 次のイベント
            productive_category_ids: 制作系カテゴリIDリスト
            browser_category_id: Browserカテゴリ ID
            glue_tolerance: 許容時間(秒)
        
        Returns:
            True: Glue適用, False: 適用しない
        """
        # 1. 前のイベントが制作系
        if prev_event.get("category_id") not in productive_category_ids:
            return False
        
        # 2. 中間のイベントが調べ物
        if middle_event.get("category_id") != browser_category_id:
            return False
        
        # 3. 次のイベントが制作系
        if next_event.get("category_id") not in productive_category_ids:
            return False
        
        # 4. 中間のイベントの長さチェック
        if middle_event.get("start_at") and middle_event.get("end_at"):
            start = datetime.fromisoformat(middle_event["start_at"]) if isinstance(middle_event["start_at"], str) else middle_event["start_at"]
            end = datetime.fromisoformat(middle_event["end_at"]) if isinstance(middle_event["end_at"], str) else middle_event["end_at"]
            duration = (end - start).total_seconds()
            
            if duration > glue_tolerance:
                return False
        
        return True
    
    def process_recent_events(self, hours: int = 24) -> None:
        """
        最近のイベントにGlueルールを適用
        
        Args:
            hours: 処理対象の時間範囲(時間)
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        events = self.db.get_events_by_date_range(start_time, end_time)
        
        if events:
            self.apply_glue_rules(events)
            print(f"{len(events)}件のイベントにGlueルールを適用しました")
