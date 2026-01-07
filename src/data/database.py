"""
データベース管理モジュール
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import re

from ..utils.default_categories import DEFAULT_CATEGORIES, DEFAULT_RULES


class Database:
    """SQLiteデータベース管理クラス"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # デフォルトはdata/tracker.db
            base_dir = Path(__file__).parent.parent.parent
            db_path = base_dir / "data" / "tracker.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None
    
    def connect(self) -> None:
        """データベースに接続"""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # 辞書形式で結果を取得
    
    def close(self) -> None:
        """データベース接続を閉じる"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def initialize(self) -> None:
        """データベースを初期化(テーブル作成)"""
        self.connect()
        cursor = self.conn.cursor()
        
        # カテゴリテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                color TEXT,
                parent_id INTEGER,
                is_productive BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES categories(id)
            )
        """)
        
        # 分類ルールテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_target TEXT NOT NULL,
                pattern TEXT NOT NULL,
                is_regex BOOLEAN DEFAULT 0,
                category_id INTEGER NOT NULL,
                priority INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        """)
        
        # イベントログテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_at TIMESTAMP NOT NULL,
                end_at TIMESTAMP,
                app_name TEXT NOT NULL,
                process_name TEXT,
                window_title TEXT,
                category_id INTEGER,
                is_afk BOOLEAN DEFAULT 0,
                is_glued BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        """)
        
        # 集中セッションテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_at TIMESTAMP NOT NULL,
                end_at TIMESTAMP NOT NULL,
                category_id INTEGER,
                duration_minutes INTEGER,
                event_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        """)
        
        self.conn.commit()
        
        # デフォルトデータの投入(初回のみ)
        self._initialize_default_data()
    
    def _initialize_default_data(self) -> None:
        """デフォルトカテゴリとルールを投入"""
        cursor = self.conn.cursor()
        
        # カテゴリが空の場合のみ投入
        cursor.execute("SELECT COUNT(*) FROM categories")
        if cursor.fetchone()[0] == 0:
            for cat in DEFAULT_CATEGORIES:
                cursor.execute(
                    "INSERT INTO categories (name, color, is_productive) VALUES (?, ?, ?)",
                    (cat["name"], cat["color"], cat["is_productive"])
                )
            self.conn.commit()
        
        # ルールが空の場合のみ投入
        cursor.execute("SELECT COUNT(*) FROM rules")
        if cursor.fetchone()[0] == 0:
            for rule in DEFAULT_RULES:
                # カテゴリ名からIDを取得
                cursor.execute("SELECT id FROM categories WHERE name = ?", (rule["category"],))
                result = cursor.fetchone()
                if result:
                    category_id = result[0]
                    cursor.execute(
                        "INSERT INTO rules (match_target, pattern, is_regex, category_id, priority) VALUES (?, ?, ?, ?, ?)",
                        (rule["match_target"], rule["pattern"], rule["is_regex"], category_id, rule["priority"])
                    )
            self.conn.commit()
    
    # カテゴリ関連
    def get_all_categories(self) -> List[Dict[str, Any]]:
        """すべてのカテゴリを取得"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM categories ORDER BY id")
        return [dict(row) for row in cursor.fetchall()]
    
    def get_category_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """名前でカテゴリを取得"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM categories WHERE name = ?", (name,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_category_by_id(self, category_id: int) -> Optional[Dict[str, Any]]:
        """IDでカテゴリを取得"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    # ルール関連
    def get_all_rules(self) -> List[Dict[str, Any]]:
        """すべてのルールを取得(優先度順)"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM rules ORDER BY priority DESC, id")
        return [dict(row) for row in cursor.fetchall()]
    
    def match_category(self, app_name: str, process_name: str = None, window_title: str = None) -> Optional[int]:
        """アプリ情報からカテゴリIDを判定"""
        rules = self.get_all_rules()
        
        for rule in rules:
            target_value = None
            if rule["match_target"] == "app_name":
                target_value = app_name
            elif rule["match_target"] == "process" and process_name:
                target_value = process_name
            elif rule["match_target"] == "title" and window_title:
                target_value = window_title
            
            if target_value:
                if rule["is_regex"]:
                    # 正規表現マッチ
                    if re.search(rule["pattern"], target_value, re.IGNORECASE):
                        return rule["category_id"]
                else:
                    # 部分一致
                    if rule["pattern"].lower() in target_value.lower():
                        return rule["category_id"]
        
        # マッチしない場合は「未分類」カテゴリ
        uncategorized = self.get_category_by_name("未分類")
        return uncategorized["id"] if uncategorized else None
    
    # イベント関連
    def add_event(self, app_name: str, process_name: str = None, window_title: str = None,
                  category_id: int = None, is_afk: bool = False) -> int:
        """新しいイベントを追加"""
        cursor = self.conn.cursor()
        now = datetime.now()
        
        cursor.execute(
            """INSERT INTO events (start_at, app_name, process_name, window_title, category_id, is_afk)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (now, app_name, process_name, window_title, category_id, is_afk)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def update_event_end_time(self, event_id: int, end_at: datetime = None) -> None:
        """イベントの終了時刻を更新"""
        if end_at is None:
            end_at = datetime.now()
        
        cursor = self.conn.cursor()
        cursor.execute("UPDATE events SET end_at = ? WHERE id = ?", (end_at, event_id))
        self.conn.commit()
    
    def get_latest_event(self) -> Optional[Dict[str, Any]]:
        """最新のイベントを取得"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM events ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_events_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """日付範囲でイベントを取得"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM events WHERE start_at >= ? AND start_at < ? ORDER BY start_at",
            (start_date, end_date)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def update_event_category(self, event_id: int, category_id: int) -> None:
        """イベントのカテゴリを更新"""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE events SET category_id = ? WHERE id = ?", (category_id, event_id))
        self.conn.commit()
    
    # セッション関連
    def add_session(self, start_at: datetime, end_at: datetime, category_id: int,
                    duration_minutes: int, event_count: int) -> int:
        """集中セッションを追加"""
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO sessions (start_at, end_at, category_id, duration_minutes, event_count)
               VALUES (?, ?, ?, ?, ?)""",
            (start_at, end_at, category_id, duration_minutes, event_count)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def get_sessions_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """日付範囲でセッションを取得"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM sessions WHERE start_at >= ? AND start_at < ? ORDER BY start_at",
            (start_date, end_date)
        )
        return [dict(row) for row in cursor.fetchall()]
