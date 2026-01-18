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
        
        # 進行中セッションの状態（リアルタイム追跡用）
        self.active_session = {
            "app_name": None,
            "category_id": None,
            "start_time": None,
            "accumulated_seconds": 0,
            "last_event_end": None,
            "notified_milestones": set(),  # 通知済みの節目 (10, 20, 30...)
            "db_session_id": None  # DB保存済みセッションID
        }
    
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
    
    def on_event_change(self, app_name: str, category_id: int, is_afk: bool, 
                        event_start: datetime, event_end: datetime) -> None:
        """
        イベント変更時にセッション状態を更新（リアルタイム追跡）
        
        新仕様:
        - カテゴリが同じであれば継続してカウント
        - 10分連続使用（他カテゴリの使用がなかった）ごとに1セッション獲得
        
        Args:
            app_name: アプリ名
            category_id: カテゴリID
            is_afk: AFK状態かどうか
            event_start: イベント開始時刻
            event_end: イベント終了時刻
        """
        if is_afk:
            # AFK時は現在のセッションを確定
            self._finalize_active_session()
            return
        
        session_threshold = self.config.get("session_threshold", 10)  # 分
        duration_seconds = (event_end - event_start).total_seconds()
        
        # 同じカテゴリの継続
        if self.active_session["category_id"] == category_id:
            # 時間を加算
            old_accumulated_seconds = self.active_session["accumulated_seconds"]
            self.active_session["accumulated_seconds"] += duration_seconds
            self.active_session["last_event_end"] = event_end
            self.active_session["app_name"] = app_name  # アプリ名は最新のものに更新
            
            # セッション獲得チェック（10分ごとに1セッション）
            old_session_count = int(old_accumulated_seconds / (session_threshold * 60))
            new_session_count = int(self.active_session["accumulated_seconds"] / (session_threshold * 60))
            
            # 新しいセッションを獲得した場合
            if new_session_count > old_session_count:
                # 獲得したセッション数だけ処理
                for i in range(old_session_count + 1, new_session_count + 1):
                    session_minutes = i * session_threshold
                    if session_minutes not in self.active_session["notified_milestones"]:
                        self.active_session["notified_milestones"].add(session_minutes)
                        self._save_or_update_active_session()
                        self._send_notification(session_minutes)
        else:
            # 異なるカテゴリ → 前のセッションを確定
            self._finalize_active_session()
            
            # 新しいセッション開始
            self.active_session = {
                "app_name": app_name,
                "category_id": category_id,
                "start_time": event_start,
                "accumulated_seconds": duration_seconds,
                "last_event_end": event_end,
                "notified_milestones": set(),
                "db_session_id": None
            }
    
    def _finalize_active_session(self) -> None:
        """現在のセッションを確定してDB保存"""
        if not self.active_session["app_name"]:
            return
        
        session_threshold = self.config.get("session_threshold", 10)  # 分
        session_threshold_seconds = session_threshold * 60
        if self.active_session["accumulated_seconds"] >= session_threshold_seconds:
            self._save_or_update_active_session()
        
        # セッションリセット
        self.active_session = {
            "app_name": None,
            "category_id": None,
            "start_time": None,
            "accumulated_seconds": 0,
            "last_event_end": None,
            "notified_milestones": set(),
            "db_session_id": None
        }
    
    def _save_or_update_active_session(self) -> None:
        """進行中セッションをDBに保存または更新"""
        if not self.active_session["app_name"]:
            return
        
        duration_minutes = int(self.active_session["accumulated_seconds"] / 60)
        
        # カテゴリ情報を取得（ログ用）
        category = self.db.get_category_by_id(self.active_session["category_id"])
        category_name = category.get("name", "不明") if category else "不明"
        
        if self.active_session["db_session_id"]:
            # 既存セッションを更新
            self.db.update_session(
                session_id=self.active_session["db_session_id"],
                end_at=self.active_session["last_event_end"],
                duration_minutes=duration_minutes,
                event_count=1  # イベント数は簡略化
            )
            print(f"[セッション] 更新: ID={self.active_session['db_session_id']}, カテゴリ={category_name}, {duration_minutes}分")
        else:
            # 新規セッションを保存
            session_id = self.db.add_session(
                start_at=self.active_session["start_time"],
                end_at=self.active_session["last_event_end"],
                category_id=self.active_session["category_id"],
                duration_minutes=duration_minutes,
                event_count=1,
                main_app_name=self.active_session["app_name"]
            )
            self.active_session["db_session_id"] = session_id
            print(f"[セッション] 新規保存: ID={session_id}, カテゴリ={category_name}, {duration_minutes}分")
    
    def _send_notification(self, duration_minutes: int) -> None:
        """セッション達成通知を送信"""
        if not self.notification_manager:
            return
        
        category = self.db.get_category_by_id(self.active_session["category_id"])
        category_name = category.get("name", "不明") if category else "不明"
        
        print(f"[セッション] 通知送信: {duration_minutes}分達成 ({self.active_session['app_name']})")
        
        self.notification_manager.notify_session_complete(
            duration_minutes=duration_minutes,
            category_name=category_name,
            main_app=self.active_session["app_name"]
        )
    
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
        # キー: (start_at, main_app_name) -> session_data
        existing_sessions = self.db.get_sessions_by_date_range(start_time, end_time)
        existing_session_map = {}
        for s in existing_sessions:
            start_at = s.get("start_at")
            if isinstance(start_at, str):
                start_at = datetime.fromisoformat(start_at)
            
            # 秒未満を切り捨てて比較用にする
            start_key = start_at.replace(microsecond=0)
            app_name = s.get("main_app_name")
            existing_session_map[(start_key, app_name)] = s
        
        saved_count = 0
        for session in sessions:
            try:
                # 閾値チェック（念のため）
                if session["duration_minutes"] < 1:
                    continue
                
                # 重複チェックキー作成
                s_start = session["start_at"]
                if isinstance(s_start, str):
                    s_start = datetime.fromisoformat(s_start)
                s_start_key = s_start.replace(microsecond=0)
                s_app_name = session.get("main_app_name")
                
                session_key = (s_start_key, s_app_name)
                
                # 通知を送るかどうか
                should_notify = False
                
                if session_key in existing_session_map:
                    # 既存セッションを更新
                    existing = existing_session_map[session_key]
                    existing_id = existing["id"]
                    old_duration = existing["duration_minutes"]
                    new_duration = session["duration_minutes"]
                    
                    # 時間が変わっていれば更新
                    if new_duration != old_duration:
                        self.db.update_session(
                            session_id=existing_id,
                            end_at=session["end_at"],
                            duration_minutes=new_duration,
                            event_count=session["event_count"]
                        )
                        print(f"[セッション] 更新: ID={existing_id}, {old_duration}分 -> {new_duration}分")
                        
                        # 通知判定: 10分の節目をまたいだか？
                        # 例: 10分 -> 20分 (OK), 12分 -> 15分 (NG), 9分 -> 10分 (OK)
                        if (new_duration // 10) > (old_duration // 10):
                            should_notify = True
                else:
                    # 新規セッションを保存
                    new_id = self.db.add_session(
                        start_at=session["start_at"],
                        end_at=session["end_at"],
                        category_id=session["category_id"],
                        duration_minutes=session["duration_minutes"],
                        event_count=session["event_count"],
                        main_app_name=session.get("main_app_name")
                    )
                    saved_count += 1
                    print(f"[セッション] 新規保存: ID={new_id}, {session['duration_minutes']}分")
                    
                    # 新規作成時は常に通知（ただし閾値以上の場合）
                    session_threshold = self.config.get("session_threshold", 10)
                    if session["duration_minutes"] >= session_threshold:
                        should_notify = True
                
                # 通知処理
                if should_notify and self.notification_manager:
                    category = self.db.get_category_by_id(session["category_id"])
                    category_name = category.get("name", "不明") if category else "不明"
                    
                    print(f"[セッション] 通知送信: {session['duration_minutes']}分達成 ({s_app_name})")
                    
                    self.notification_manager.notify_session_complete(
                        duration_minutes=session["duration_minutes"],
                        category_name=category_name,
                        main_app=session.get("main_app_name", "不明")
                    )
                    
            except Exception as e:
                print(f"セッション保存エラー: {e}")
        
        if saved_count > 0:
            print(f"{saved_count}件の集中セッションを保存しました")
        
        return saved_count
