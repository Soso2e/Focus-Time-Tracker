"""
集中セッション検出モジュール
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from ..data.database import Database
from ..utils.config import get_config


class SessionDetector:
    """集中セッション検出クラス"""
    
    def __init__(self, db: Database):
        """
        Args:
            db: データベースインスタンス
        """
        self.db = db
        self.config = get_config()
    
    def detect_sessions(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        イベント列から集中セッションを検出
        
        同一カテゴリ(またはGlue許容内)で設定時間以上継続した場合、
        1つの集中セッションとして認定
        
        Args:
            events: イベントリスト
        
        Returns:
            検出されたセッションリスト
        """
        if not events:
            return []
        
        session_threshold = self.config.get("session_threshold", 10)  # 分
        threshold_seconds = session_threshold * 60
        
        sessions = []
        current_session_events = []
        current_category_id = None
        session_start = None
        
        for event in events:
            # AFK イベントはスキップ
            if event.get("is_afk", False):
                # 現在のセッションを終了
                if current_session_events:
                    session = self._finalize_session(current_session_events, threshold_seconds)
                    if session:
                        sessions.append(session)
                    current_session_events = []
                    current_category_id = None
                    session_start = None
                continue
            
            event_category_id = event.get("category_id")
            
            # セッション開始 or 継続
            if current_category_id is None:
                # 新しいセッション開始
                current_category_id = event_category_id
                current_session_events = [event]
                session_start = event.get("start_at")
            elif current_category_id == event_category_id or event.get("is_glued", False):
                # 同じカテゴリまたはGlue済み → セッション継続
                current_session_events.append(event)
            else:
                # カテゴリ変更 → 現在のセッションを終了して新しいセッション開始
                session = self._finalize_session(current_session_events, threshold_seconds)
                if session:
                    sessions.append(session)
                
                current_category_id = event_category_id
                current_session_events = [event]
                session_start = event.get("start_at")
        
        # 最後のセッションを処理
        if current_session_events:
            session = self._finalize_session(current_session_events, threshold_seconds)
            if session:
                sessions.append(session)
        
        return sessions
    
    def _finalize_session(
        self,
        events: List[Dict[str, Any]],
        threshold_seconds: int
    ) -> Optional[Dict[str, Any]]:
        """
        セッションを確定
        
        Args:
            events: セッションを構成するイベントリスト
            threshold_seconds: セッション認定のしきい値(秒)
        
        Returns:
            セッション情報(しきい値未満の場合はNone)
        """
        if not events:
            return None
        
        # 開始・終了時刻を取得
        start_at = events[0].get("start_at")
        end_at = events[-1].get("end_at")
        
        if not start_at or not end_at:
            return None
        
        # datetime型に変換
        if isinstance(start_at, str):
            start_at = datetime.fromisoformat(start_at)
        if isinstance(end_at, str):
            end_at = datetime.fromisoformat(end_at)
        
        # 継続時間を計算
        duration_seconds = (end_at - start_at).total_seconds()
        
        # しきい値チェック
        if duration_seconds < threshold_seconds:
            return None
        
        # セッション情報を作成
        category_id = events[0].get("category_id")
        duration_minutes = int(duration_seconds / 60)
        
        return {
            "start_at": start_at,
            "end_at": end_at,
            "category_id": category_id,
            "duration_minutes": duration_minutes,
            "event_count": len(events)
        }
    
    def process_and_save_sessions(self, hours: int = 24) -> int:
        """
        最近のイベントからセッションを検出してデータベースに保存
        
        Args:
            hours: 処理対象の時間範囲(時間)
        
        Returns:
            保存されたセッション数
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        events = self.db.get_events_by_date_range(start_time, end_time)
        sessions = self.detect_sessions(events)
        
        saved_count = 0
        for session in sessions:
            try:
                self.db.add_session(
                    start_at=session["start_at"],
                    end_at=session["end_at"],
                    category_id=session["category_id"],
                    duration_minutes=session["duration_minutes"],
                    event_count=session["event_count"]
                )
                saved_count += 1
            except Exception as e:
                print(f"セッション保存エラー: {e}")
        
        if saved_count > 0:
            print(f"{saved_count}件の集中セッションを保存しました")
        
        return saved_count
