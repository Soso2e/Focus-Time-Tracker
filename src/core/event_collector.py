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
    
    def __init__(self, db: Database):
        """
        Args:
            db: データベースインスタンス
        """
        self.db = db
        self.config = get_config()
        self.current_event_id: Optional[int] = None
        self.current_app_name: Optional[str] = None
    
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
    
    def update_current_event_afk_status(self, is_afk: bool) -> None:
        """
        現在のイベントのAFK状態を更新
        
        Args:
            is_afk: AFK状態かどうか
        """
        if self.current_event_id is not None:
            # TODO: AFK状態の更新ロジックを実装
            pass
    
    def finalize_current_event(self) -> None:
        """現在のイベントを終了"""
        if self.current_event_id is not None:
            self.db.update_event_end_time(self.current_event_id)
            self.current_event_id = None
            self.current_app_name = None
