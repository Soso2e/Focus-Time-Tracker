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
                main_app_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        """)
        
        # インデックス作成（パフォーマンス最適化）
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_start_at ON events(start_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_category_id ON events(category_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_app_name ON events(app_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_start_at ON sessions(start_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_category_id ON sessions(category_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rules_category_id ON rules(category_id)")
        
        # 既存のsessionsテーブルにmain_app_nameカラムがない場合は追加（マイグレーション）
        cursor.execute("PRAGMA table_info(sessions)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'main_app_name' not in columns:
            try:
                cursor.execute("ALTER TABLE sessions ADD COLUMN main_app_name TEXT")
                print("sessionsテーブルにmain_app_nameカラムを追加しました")
            except Exception as e:
                print(f"カラム追加エラー: {e}")
        
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
    
    def add_category(self, name: str, color: str = "#B2BEC3", is_productive: bool = True, parent_id: int = None) -> int:
        """カテゴリを追加"""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO categories (name, color, is_productive, parent_id) VALUES (?, ?, ?, ?)",
            (name, color, is_productive, parent_id)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def update_category(self, category_id: int, name: str = None, color: str = None, is_productive: bool = None) -> None:
        """カテゴリを更新"""
        cursor = self.conn.cursor()
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if color is not None:
            updates.append("color = ?")
            params.append(color)
        if is_productive is not None:
            updates.append("is_productive = ?")
            params.append(is_productive)
        
        if updates:
            params.append(category_id)
            cursor.execute(f"UPDATE categories SET {', '.join(updates)} WHERE id = ?", params)
            self.conn.commit()
    
    def delete_category(self, category_id: int) -> None:
        """カテゴリを削除（関連ルールも削除）"""
        cursor = self.conn.cursor()
        # 関連ルールを削除
        cursor.execute("DELETE FROM rules WHERE category_id = ?", (category_id,))
        # カテゴリを削除
        cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        self.conn.commit()
    
    # ルール関連
    def get_all_rules(self) -> List[Dict[str, Any]]:
        """すべてのルールを取得(優先度順)"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM rules ORDER BY priority DESC, id")
        return [dict(row) for row in cursor.fetchall()]
    
    def add_rule(self, match_target: str, pattern: str, category_id: int, 
                 is_regex: bool = False, priority: int = 10) -> int:
        """ルールを追加"""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO rules (match_target, pattern, is_regex, category_id, priority) VALUES (?, ?, ?, ?, ?)",
            (match_target, pattern, is_regex, category_id, priority)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def update_rule(self, rule_id: int, match_target: str = None, pattern: str = None, 
                    category_id: int = None, is_regex: bool = None, priority: int = None) -> None:
        """ルールを更新"""
        cursor = self.conn.cursor()
        updates = []
        params = []
        
        if match_target is not None:
            updates.append("match_target = ?")
            params.append(match_target)
        if pattern is not None:
            updates.append("pattern = ?")
            params.append(pattern)
        if category_id is not None:
            updates.append("category_id = ?")
            params.append(category_id)
        if is_regex is not None:
            updates.append("is_regex = ?")
            params.append(is_regex)
        if priority is not None:
            updates.append("priority = ?")
            params.append(priority)
        
        if updates:
            params.append(rule_id)
            cursor.execute(f"UPDATE rules SET {', '.join(updates)} WHERE id = ?", params)
            self.conn.commit()
    
    def delete_rule(self, rule_id: int) -> None:
        """ルールを削除"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
        self.conn.commit()
    
    def get_rules_by_category(self, category_id: int) -> List[Dict[str, Any]]:
        """特定カテゴリのルールを取得"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM rules WHERE category_id = ? ORDER BY priority DESC", (category_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def match_category(self, app_name: str, process_name: str = None, window_title: str = None) -> Optional[int]:
        """
        アプリ情報からカテゴリIDを判定
        
        優先順位（FIXED）:
        1. 高優先度ルール（priority >= 10）- アプリ名とプロセス名
        2. ファイル拡張子チェック（エディタ/ブラウザのみ）
        3. 通常優先度ルール（priority < 10）
        4. ウィンドウタイトル全体のルール
        """
        # ルールを取得
        rules = self.get_all_rules()
        
        # 高優先度ルールと通常優先度ルールに分離
        high_priority_rules = [r for r in rules if r["priority"] >= 10]
        normal_priority_rules = [r for r in rules if r["priority"] < 10]
        
        # 1. 高優先度プロセス名ルール
        if process_name:
            for rule in high_priority_rules:
                if rule["match_target"] == "process":
                    if rule["is_regex"]:
                        if re.search(rule["pattern"], process_name, re.IGNORECASE):
                            return rule["category_id"]
                    else:
                        if rule["pattern"].lower() in process_name.lower():
                            return rule["category_id"]
        
        # 2. 高優先度アプリ名ルール（Maya, Blenderなど）
        if app_name:
            for rule in high_priority_rules:
                if rule["match_target"] == "app_name":
                    if rule["is_regex"]:
                        if re.search(rule["pattern"], app_name, re.IGNORECASE):
                            return rule["category_id"]
                    else:
                        if rule["pattern"].lower() in app_name.lower():
                            return rule["category_id"]
        
        # 3. ファイル拡張子チェック（エディタ/ブラウザ/ターミナルのみ対象）
        # Note: 3Dソフトなどの明確なアプリは上記でマッチ済み
        if window_title and app_name:
            # エディタ/IDE系のアプリのみ拡張子チェックを適用
            editor_apps = [
                "code", "visual studio", "pycharm", "intellij", "sublime", "atom",
                "notepad", "vim", "emacs", "vscode", "antigravity", "cursor"
            ]
            # ブラウザ系（タイトルにURLや拡張子が含まれる可能性）
            browser_apps = ["chrome", "firefox", "safari", "edge", "brave", "arc"]
            # ターミナル系
            terminal_apps = ["windowsterminal", "powershell", "cmd", "terminal"]
            
            app_name_lower = app_name.lower()
            is_editor_or_browser = any(app in app_name_lower for app in editor_apps + browser_apps + terminal_apps)
            
            if is_editor_or_browser:
                # コーディング関連のファイル拡張子リスト
                coding_extensions = [
                    '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.hpp',
                    '.cs', '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.html', '.css', '.scss',
                    '.sass', '.less', '.json', '.xml', '.yaml', '.yml', '.md', '.sql', '.sh', '.bash',
                    '.bat', '.ps1', '.r', '.m', '.scala', '.pl', '.lua', '.vim', '.ini', '.cfg',
                    '.conf', '.toml', '.dart', '.vue', '.svelte', '.astro', '.txt'
                ]
                
                window_title_lower = window_title.lower()
                for ext in coding_extensions:
                    if ext in window_title_lower:
                        # 「コーディング」カテゴリを取得
                        coding_category = self.get_category_by_name("コーディング")
                        if coding_category:
                            return coding_category["id"]
                        break
        
        # 4. 通常優先度プロセス名ルール
        if process_name:
            for rule in normal_priority_rules:
                if rule["match_target"] == "process":
                    if rule["is_regex"]:
                        if re.search(rule["pattern"], process_name, re.IGNORECASE):
                            return rule["category_id"]
                    else:
                        if rule["pattern"].lower() in process_name.lower():
                            return rule["category_id"]
        
        # 5. 通常優先度アプリ名ルール
        if app_name:
            for rule in normal_priority_rules:
                if rule["match_target"] == "app_name":
                    if rule["is_regex"]:
                        if re.search(rule["pattern"], app_name, re.IGNORECASE):
                            return rule["category_id"]
                    else:
                        if rule["pattern"].lower() in app_name.lower():
                            return rule["category_id"]
        
        # 6. ウィンドウタイトル全体のルールをチェック（最低優先度）
        if window_title:
            for rule in rules:
                if rule["match_target"] == "title":
                    if rule["is_regex"]:
                        if re.search(rule["pattern"], window_title, re.IGNORECASE):
                            return rule["category_id"]
                    else:
                        if rule["pattern"].lower() in window_title.lower():
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
    
    def get_event_by_id(self, event_id: int) -> Optional[Dict[str, Any]]:
        """IDでイベントを取得"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
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
    
    def reclassify_events(self, start_date: datetime = None, end_date: datetime = None) -> int:
        """
        イベントを再分類する
        
        Args:
            start_date: 開始日時（Noneの場合は全期間）
            end_date: 終了日時（Noneの場合は全期間）
        
        Returns:
            再分類されたイベント数
        """
        cursor = self.conn.cursor()
        
        # 対象イベントを取得
        if start_date and end_date:
            cursor.execute(
                "SELECT id, app_name, process_name, window_title FROM events WHERE start_at >= ? AND start_at < ?",
                (start_date, end_date)
            )
        else:
            cursor.execute("SELECT id, app_name, process_name, window_title FROM events")
        
        events = cursor.fetchall()
        updated_count = 0
        
        for event in events:
            event_id = event[0]
            app_name = event[1]
            process_name = event[2]
            window_title = event[3]
            
            # 新しいカテゴリを判定
            new_category_id = self.match_category(app_name, process_name, window_title)
            
            # カテゴリを更新
            cursor.execute(
                "UPDATE events SET category_id = ? WHERE id = ?",
                (new_category_id, event_id)
            )
            updated_count += 1
        
        self.conn.commit()
        return updated_count

    
    # セッション関連
    def add_session(self, start_at: datetime, end_at: datetime, category_id: int,
                    duration_minutes: int, event_count: int, main_app_name: str = None) -> int:
        """集中セッションを追加"""
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO sessions (start_at, end_at, category_id, duration_minutes, event_count, main_app_name)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (start_at, end_at, category_id, duration_minutes, event_count, main_app_name)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def update_session(self, session_id: int, end_at: datetime, duration_minutes: int, event_count: int) -> None:
        """集中セッションを更新"""
        cursor = self.conn.cursor()
        cursor.execute(
            """UPDATE sessions 
               SET end_at = ?, duration_minutes = ?, event_count = ?
               WHERE id = ?""",
            (end_at, duration_minutes, event_count, session_id)
        )
        self.conn.commit()
    
    def get_sessions_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """日付範囲でセッションを取得"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM sessions WHERE start_at >= ? AND start_at < ? ORDER BY start_at",
            (start_date, end_date)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    # データ削除メソッド
    
    def delete_events_by_date_range(self, start_date: datetime, end_date: datetime) -> int:
        """
        期間指定でイベントを削除
        
        Args:
            start_date: 開始日時
            end_date: 終了日時
        
        Returns:
            削除されたイベント数
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "DELETE FROM events WHERE start_at >= ? AND start_at < ?",
            (start_date, end_date)
        )
        self.conn.commit()
        return cursor.rowcount
    
    def delete_sessions_by_date_range(self, start_date: datetime, end_date: datetime) -> int:
        """
        期間指定でセッションを削除
        
        Args:
            start_date: 開始日時
            end_date: 終了日時
        
        Returns:
            削除されたセッション数
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "DELETE FROM sessions WHERE start_at >= ? AND start_at < ?",
            (start_date, end_date)
        )
        self.conn.commit()
        return cursor.rowcount
    
    def delete_today_data(self) -> tuple[int, int]:
        """
        今日のデータ（イベントとセッション）を削除
        
        Returns:
            (削除されたイベント数, 削除されたセッション数)
        """
        from datetime import datetime, timedelta
        
        # 今日の0時から明日の0時まで
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start + timedelta(days=1)
        
        events_deleted = self.delete_events_by_date_range(today_start, tomorrow_start)
        sessions_deleted = self.delete_sessions_by_date_range(today_start, tomorrow_start)
        
        return (events_deleted, sessions_deleted)
    
    def delete_events_by_app_name(self, app_name: str) -> int:
        """
        アプリ名でイベントを削除
        
        Args:
            app_name: アプリ名
        
        Returns:
            削除されたイベント数
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "DELETE FROM events WHERE app_name = ?",
            (app_name,)
        )
        self.conn.commit()
        return cursor.rowcount
    
    def delete_events_by_process_name(self, process_name: str) -> int:
        """
        プロセス名でイベントを削除
        
        Args:
            process_name: プロセス名
        
        Returns:
            削除されたイベント数
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "DELETE FROM events WHERE process_name = ?",
            (process_name,)
        )
        self.conn.commit()
        return cursor.rowcount
    
    def delete_session_by_id(self, session_id: int) -> bool:
        """
        セッションIDでセッションを削除
        
        Args:
            session_id: セッションID
        
        Returns:
            削除成功したかどうか
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "DELETE FROM sessions WHERE id = ?",
            (session_id,)
        )
        self.conn.commit()
        return cursor.rowcount > 0
    
    def delete_all_sessions(self) -> int:
        """
        全セッションを削除
        
        Returns:
            削除されたセッション数
        """
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM sessions")
        self.conn.commit()
        return cursor.rowcount
