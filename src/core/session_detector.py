"""
集中セッション検出モジュール
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from ..data.database import Database
from ..utils.config import get_config


class SessionDetector:
    """集中セッション検出クラス"""
    
    def __init__(self, db: Database, notification_manager=None):
        """
        Args:
            db: データベースインスタンス
            notification_manager: 通知マネージャー（オプション）
        """
        self.db = db
        self.config = get_config()
        self.notification_manager = notification_manager
    
    def detect_sessions(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        イベント列から集中セッションを検出（新ロジック）
        
        - 同じアプリが連続している場合、セッション候補とする
        - 指定時間（デフォルト10分）経過でセッションとして記録
        - 調べ物・連絡カテゴリの1分未満の中断は許容
        
        Args:
            events: イベントリスト
        
        Returns:
            検出されたセッションリスト
        """
        if not events:
            return []
        
        session_threshold = self.config.get("session_threshold", 10)  # 分
        interruption_max_duration = self.config.get("interruption_max_duration", 60)  # 秒
        
        sessions = []
        current_session_events = []
        current_main_app = None
        
        for event in events:
            # AFKイベントはスキップ
            if event.get("is_afk", False):
                # 現在のセッションを確定
                if current_session_events and current_main_app:
                    session = self._finalize_session(current_session_events, session_threshold, current_main_app)
                    if session:
                        sessions.append(session)
                    current_session_events = []
                    current_main_app = None
                continue
            
            app_name = event.get("app_name")
            
            # セッション開始
            if not current_main_app:
                current_main_app = app_name
                current_session_events = [event]
                continue
            
            # 同じアプリの場合、セッションに追加
            if app_name == current_main_app:
                current_session_events.append(event)
                continue
            
            # 異なるアプリの場合、中断許容判定
            if self._is_interruption_allowed(event, interruption_max_duration):
                # 中断を許容してセッションに追加
                current_session_events.append(event)
                continue
            
            # 中断が許容されない場合、現在のセッションを確定
            session = self._finalize_session(current_session_events, session_threshold, current_main_app)
            if session:
                sessions.append(session)
            
            # 新しいセッション開始
            current_main_app = app_name
            current_session_events = [event]
        
        # 最後のセッションを確定
        if current_session_events:
            session = self._finalize_session(current_session_events, session_threshold, current_main_app)
            if session:
                sessions.append(session)
        
        return sessions
    
    def _is_interruption_allowed(self, event: Dict[str, Any], max_duration: int) -> bool:
        """
        中断が許容されるかを判定
        
        Args:
            event: イベント
            max_duration: 最大許容時間（秒）
        
        Returns:
            中断が許容される場合True
        """
        # イベントの継続時間を計算
        start = event.get("start_at")
        end = event.get("end_at")
        
        if not start or not end:
            return False
        
        if isinstance(start, str):
            start = datetime.fromisoformat(start)
        if isinstance(end, str):
            end = datetime.fromisoformat(end)
        
        duration = (end - start).total_seconds()
        
        # 1分以上の場合は許容しない
        if duration >= max_duration:
            return False
        
        # カテゴリが調べ物または連絡の場合は許容
        category_id = event.get("category_id")
        if not category_id:
            return False
        
        category = self.db.get_category_by_id(category_id)
        if not category:
            return False
        
        category_name = category.get("name", "").lower()
        
        # 調べ物・連絡カテゴリの判定
        lookup_keywords = ["調べ物", "リサーチ", "research", "検索"]
        communication_keywords = ["連絡", "コミュニケーション", "communication", "メール", "チャット"]
        
        for keyword in lookup_keywords + communication_keywords:
            if keyword.lower() in category_name:
                return True
        
        return False
    
    def _finalize_session(self, events: List[Dict[str, Any]], session_threshold: int, main_app_name: str) -> Optional[Dict[str, Any]]:
        """
        イベントリストからセッションを作成
        
        Args:
            events: イベントリスト
            session_threshold: セッション閾値（分）
            main_app_name: メインアプリ名（連続使用されたアプリ）
        
        Returns:
            セッション情報（閾値未満の場合はNone）
        """
        if not events:
            return None
        
        # 開始時刻と終了時刻
        start_at = events[0].get("start_at")
        end_at = events[-1].get("end_at")
        
        if not start_at or not end_at:
            return None
        
        if isinstance(start_at, str):
            start_at = datetime.fromisoformat(start_at)
        if isinstance(end_at, str):
            end_at = datetime.fromisoformat(end_at)
        
        # 総時間を計算（実際の継続時間）
        total_duration_seconds = 0
        for event in events:
            event_start = event.get("start_at")
            event_end = event.get("end_at")
            
            if event_start and event_end:
                if isinstance(event_start, str):
                    event_start = datetime.fromisoformat(event_start)
                if isinstance(event_end, str):
                    event_end = datetime.fromisoformat(event_end)
                
                total_duration_seconds += (event_end - event_start).total_seconds()
        
        threshold_seconds = session_threshold * 60
        
        # 閾値未満の場合はセッションとして認めない
        if total_duration_seconds < threshold_seconds:
            return None
        
        # 実際の継続時間（分）
        actual_duration_minutes = int(total_duration_seconds / 60)
        
        # カテゴリを特定（メインアプリのカテゴリ）
        main_category_id = None
        for event in events:
            if event.get("app_name") == main_app_name:
                main_category_id = event.get("category_id")
                break
        
        # メインカテゴリが見つからない場合は最初のイベントのカテゴリ
        if not main_category_id:
            main_category_id = events[0].get("category_id")
        
        # デバッグ情報
        print(f"\n[セッション検出] {start_at.strftime('%H:%M')} - {end_at.strftime('%H:%M')}")
        print(f"  メインアプリ: {main_app_name}")
        print(f"  継続時間: {actual_duration_minutes}分")
        
        cat = self.db.get_category_by_id(main_category_id)
        cat_name = cat.get("name", "不明") if cat else "不明"
        print(f"  カテゴリ: {cat_name}")
        
        return {
            "start_at": start_at,
            "end_at": end_at,
            "category_id": main_category_id,
            "duration_minutes": actual_duration_minutes,
            "event_count": len(events),
            "main_app_name": main_app_name
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
        
        # 既存のセッションを取得（重複チェック用）
        existing_sessions = self.db.get_sessions_by_date_range(start_time, end_time)
        existing_session_times = {
            (s.get("start_at"), s.get("end_at")) for s in existing_sessions
        }
        
        saved_count = 0
        for session in sessions:
            try:
                # 閾値チェック（念のため）
                if session["duration_minutes"] < 1:
                    print(f"[セッション] スキップ: 継続時間が短すぎます ({session['duration_minutes']}分)")
                    continue
                
                # 重複チェック
                session_key = (session["start_at"], session["end_at"])
                if session_key in existing_session_times:
                    continue  # 既に保存済み
                
                self.db.add_session(
                    start_at=session["start_at"],
                    end_at=session["end_at"],
                    category_id=session["category_id"],
                    duration_minutes=session["duration_minutes"],
                    event_count=session["event_count"],
                    main_app_name=session.get("main_app_name")
                )
                saved_count += 1
                
                print(f"[セッション] 新しいセッションを保存: {session['duration_minutes']}分 / {session.get('main_app_name', '不明')}")
                
                # 通知を送信
                if self.notification_manager:
                    # カテゴリ名を取得
                    category = self.db.get_category_by_id(session["category_id"])
                    category_name = category.get("name", "不明") if category else "不明"
                    
                    print(f"[セッション] 通知を送信: {category_name} / {session.get('main_app_name', '不明')}")
                    
                    self.notification_manager.notify_session_complete(
                        duration_minutes=session["duration_minutes"],
                        category_name=category_name,
                        main_app=session.get("main_app_name", "不明")
                    )
                else:
                    print("[セッション] 通知マネージャーが設定されていません")
            except Exception as e:
                print(f"セッション保存エラー: {e}")
        
        if saved_count > 0:
            print(f"{saved_count}件の集中セッションを保存しました")
        
        return saved_count
