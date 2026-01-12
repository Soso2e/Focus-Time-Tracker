
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# srcディレクトリにパスを通す
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from core.session_detector import SessionDetector

# モッククラスの定義
class MockDatabase:
    def __init__(self):
        self.events = []
        self.sessions = []
        self.categories = {
            1: {"id": 1, "name": "Work", "color": "#FF0000"},
            2: {"id": 2, "name": "調べ物", "color": "#00FF00"},
            3: {"id": 3, "name": "Other", "color": "#0000FF"}
        }
        self.session_counter = 1

    def get_events_by_date_range(self, start: datetime, end: datetime):
        return [e for e in self.events if start <= e["start_at"] < end]

    def get_sessions_by_date_range(self, start: datetime, end: datetime):
        return [s for s in self.sessions if start <= s["start_at"] < end]

    def get_category_by_id(self, cat_id):
        return self.categories.get(cat_id)

    def add_session(self, start_at, end_at, category_id, duration_minutes, event_count, main_app_name):
        session = {
            "id": self.session_counter,
            "start_at": start_at,
            "end_at": end_at,
            "category_id": category_id,
            "duration_minutes": duration_minutes,
            "event_count": event_count,
            "main_app_name": main_app_name
        }
        self.sessions.append(session)
        self.session_counter += 1
        print(f"[DB] Add Session: ID={session['id']}, Dur={duration_minutes}m")
        return session["id"]

    def update_session(self, session_id, end_at, duration_minutes, event_count):
        for s in self.sessions:
            if s["id"] == session_id:
                s["end_at"] = end_at
                s["duration_minutes"] = duration_minutes
                s["event_count"] = event_count
                print(f"[DB] Update Session: ID={session_id}, Dur={duration_minutes}m")
                return

class MockNotificationManager:
    def __init__(self):
        self.notifications = []

    def notify_session_complete(self, duration_minutes, category_name, main_app):
        print(f"[Notify] Session Complete: {duration_minutes}m, {category_name}, {main_app}")
        self.notifications.append({
            "duration": duration_minutes,
            "category": category_name,
            "app": main_app
        })

# テスト実行
def run_tests():
    print("=== セッションロジック検証開始 ===")
    
    db = MockDatabase()
    notifier = MockNotificationManager()
    detector = SessionDetector(db, notifier)
    
    # SessionDetectorのconfigを直接上書きしてテストしやすくする
    detector.config = {
        "session_threshold": 10,
        "interruption_max_duration": 60
    }
    
    base_time = datetime(2026, 1, 1, 10, 0, 0)
    
    print("\n--- テスト1: 単純なセッション作成 (10分) ---")
    # 10分間のイベントを作成
    events1 = []
    for i in range(10): # 0分から9分まで
        events1.append({
            "app_name": "Maya",
            "category_id": 1,
            "start_at": base_time + timedelta(minutes=i),
            "end_at": base_time + timedelta(minutes=i+1),
            "is_afk": False
        })
    
    db.events = events1
    saved_count = detector.process_and_save_sessions(hours=1)
    
    assert saved_count == 1, f"セッションが1つ保存されるべき (actual: {saved_count})"
    assert len(db.sessions) == 1
    assert db.sessions[0]["duration_minutes"] == 10
    assert len(notifier.notifications) == 1, "初回なので通知されるべき"
    assert notifier.notifications[0]["duration"] == 10
    print("✓ テスト1 クリア")
    
    print("\n--- テスト2: 15分経過 (更新のみ、通知なし) ---")
    # 5分追加
    events2 = events1.copy()
    for i in range(10, 15):
        events2.append({
            "app_name": "Maya",
            "category_id": 1,
            "start_at": base_time + timedelta(minutes=i),
            "end_at": base_time + timedelta(minutes=i+1),
            "is_afk": False
        })
    
    db.events = events2
    # 前回の通知をクリア
    notifier.notifications = []
    
    saved_count = detector.process_and_save_sessions(hours=1)
    
    assert saved_count == 0, "新規保存はゼロであるべき (更新のみ)"
    assert len(db.sessions) == 1, "セッション数は1のまま"
    assert db.sessions[0]["duration_minutes"] == 15, "時間は15分に更新されるべき"
    assert len(notifier.notifications) == 0, "15分では通知されないべき (10分台)"
    print("✓ テスト2 クリア")
    
    print("\n--- テスト3: 20分経過 (更新と通知更新) ---")
    # さらに5分追加 (計20分)
    events3 = events2.copy()
    for i in range(15, 20):
        events3.append({
            "app_name": "Maya",
            "category_id": 1,
            "start_at": base_time + timedelta(minutes=i),
            "end_at": base_time + timedelta(minutes=i+1),
            "is_afk": False
        })
    
    db.events = events3
    saved_count = detector.process_and_save_sessions(hours=1)
    
    assert db.sessions[0]["duration_minutes"] == 20
    assert len(notifier.notifications) == 1, "20分になったので通知されるべき"
    assert notifier.notifications[0]["duration"] == 20
    print("✓ テスト3 クリア")
    
    print("\n--- テスト4: Glue機能 (調べ物による中断) ---")
    # 新しい時間軸
    base_time2 = datetime(2026, 1, 1, 12, 0, 0)
    db.events = []
    db.sessions = []
    notifier.notifications = []
    
    events_glue = []
    # 5分 Maya
    for i in range(5):
        events_glue.append({
            "app_name": "Maya", 
            "category_id": 1, 
            "start_at": base_time2 + timedelta(minutes=i), 
            "end_at": base_time2 + timedelta(minutes=i+1),
            "is_afk": False
        })
    
    # 30秒 Chrome (調べ物)
    events_glue.append({
        "app_name": "Chrome",
        "category_id": 2, # 調べ物
        "start_at": base_time2 + timedelta(minutes=5),
        "end_at": base_time2 + timedelta(minutes=5, seconds=30),
        "is_afk": False
    })
    
    # 4分30秒 Maya
    events_glue.append({
        "app_name": "Maya",
        "category_id": 1,
        "start_at": base_time2 + timedelta(minutes=5, seconds=30),
        "end_at": base_time2 + timedelta(minutes=10),
        "is_afk": False
    })
    
    db.events = events_glue
    
    # これで合計10分。Glueが機能すれば1つのセッション(10分)になるはず
    saved_count = detector.process_and_save_sessions(hours=1)
    
    assert len(db.sessions) == 1, "Glueにより1つのセッションになるべき"
    assert db.sessions[0]["duration_minutes"] == 10, "中断含めて10分とみなされる"
    assert db.sessions[0]["main_app_name"] == "Maya", "メインアプリはMaya"
    print("✓ テスト4 クリア")

    print("\n=== すべての検証が完了しました ===")

if __name__ == "__main__":
    run_tests()
