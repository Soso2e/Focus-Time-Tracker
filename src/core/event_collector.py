"""
イベント収集・記録モジュール
"""
from datetime import datetime
from typing import Optional

from .monitor import WindowInfo
from ..data.database import Database
from ..utils.config import get_config


class EventCollector:
    """イベント収集・記録クラス"""
    
    def __init__(self, db: Database, session_detector=None):
        """
        Args:
            db: データベースインスタンス
            session_detector: セッション検出器（オプション）
        """
        self.db = db
        self.config = get_config()
        self.session_detector = session_detector
        self.current_event_id: Optional[int] = None
        self.current_app_name: Optional[str] = None
        self.previous_event_id: Optional[int] = None  # 前のイベントIDを記憶
    
    def on_window_change(self, window_info: WindowInfo, is_afk: bool = False) -> None:
        """
        ウィンドウ変更時の処理
        
        Args:
            window_info: ウィンドウ情報
            is_afk: AFK状態かどうか
        """
        # ブラックリストチェック
        blacklist = self.config.get("blacklist_apps", [])
        if any(app.lower() in window_info.app_name.lower() for app in blacklist):
            print(f"ブラックリストアプリをスキップ: {window_info.app_name}")
            return
        
        # ウィンドウタイトル保存設定
        window_title = None
        if self.config.get("save_window_titles", False):
            window_title = window_info.window_title
        
        # カテゴリ自動判定
        category_id = self.db.match_category(
            window_info.app_name,
            window_info.process_name,
            window_info.window_title
        )
        
        # 前のイベントを終了
        if self.current_event_id is not None:
            self.db.update_event_end_time(self.current_event_id)
            self.previous_event_id = self.current_event_id  # 前のイベントIDを保存
        
        # 新しいイベントを追加
        self.current_event_id = self.db.add_event(
            app_name=window_info.app_name,
            process_name=window_info.process_name,
            window_title=window_title,
            category_id=category_id,
            is_afk=is_afk
        )
        
        self.current_app_name = window_info.app_name
        print(f"イベント記録: {window_info.app_name} (カテゴリID: {category_id})")
        
        # セッション状態を更新（前のイベント情報を使用）
        if self.session_detector and self.previous_event_id:
            # 前のイベント情報を取得（既に終了済み）
            prev_event = self.db.get_event_by_id(self.previous_event_id)
            if prev_event and prev_event.get("end_at"):
                self.session_detector.on_event_change(
                    app_name=prev_event["app_name"],
                    category_id=prev_event["category_id"],
                    is_afk=prev_event.get("is_afk", False),
                    event_start=prev_event["start_at"] if isinstance(prev_event["start_at"], datetime) else datetime.fromisoformat(prev_event["start_at"]),
                    event_end=prev_event["end_at"] if isinstance(prev_event["end_at"], datetime) else datetime.fromisoformat(prev_event["end_at"])
                )
    
    def update_current_event_end_time(self) -> None:
        """
        現在のイベントの終了時刻を現在時刻に更新
        (ロングランイベントの進行状況をDBに反映させるため)
        """
        if self.current_event_id is not None:
            self.db.update_event_end_time(self.current_event_id)
            
            # セッション状態も更新（連続作業時のセッション追跡）
            if self.session_detector:
                current_event = self.db.get_event_by_id(self.current_event_id)
                if current_event and current_event.get("end_at"):
                    self.session_detector.on_event_change(
                        app_name=current_event["app_name"],
                        category_id=current_event["category_id"],
                        is_afk=current_event.get("is_afk", False),
                        event_start=current_event["start_at"] if isinstance(current_event["start_at"], datetime) else datetime.fromisoformat(current_event["start_at"]),
                        event_end=current_event["end_at"] if isinstance(current_event["end_at"], datetime) else datetime.fromisoformat(current_event["end_at"])
                    )
            
    def update_current_event_afk_status(self, is_afk: bool) -> None:
        """
        現在のイベントのAFK状態を更新
        
        Args:
            is_afk: AFK状態かどうか
        """
        if self.current_event_id is not None:
            cursor = self.db.conn.cursor()
            cursor.execute(
                "UPDATE events SET is_afk = ? WHERE id = ?",
                (is_afk, self.current_event_id)
            )
            self.db.conn.commit()
            print(f"イベントID {self.current_event_id} のAFK状態を {is_afk} に更新")
    
    def finalize_current_event(self) -> None:
        """現在のイベントを終了"""
        if self.current_event_id is not None:
            self.db.update_event_end_time(self.current_event_id)
            self.current_event_id = None
            self.current_app_name = None
