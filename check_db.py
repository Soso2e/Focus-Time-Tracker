# -*- coding: utf-8 -*-
"""データベースの内容を確認するスクリプト"""
import sqlite3
from pathlib import Path
import sys

# UTF-8出力を強制
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

db_path = Path(__file__).parent / "data" / "tracker.db"
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

print("=" * 80)
print("最新のセッション (20件)")
print("=" * 80)
cursor.execute("""
    SELECT s.id, s.start_at, s.end_at, c.name, s.duration_minutes, s.main_app_name 
    FROM sessions s
    LEFT JOIN categories c ON s.category_id = c.id
    ORDER BY s.start_at DESC 
    LIMIT 20
""")
for row in cursor.fetchall():
    start = row[1][11:16] if row[1] else "?"  # HH:MM部分を抽出
    end = row[2][11:16] if row[2] else "?"
    print(f"ID:{row[0]:3d} | {start}~{end} | {row[4]:3d}分 | {row[3]:12s} | {row[5]}")

print("\n" + "=" * 80)
print("最新のイベント (Maya関連、30件)")
print("=" * 80)
cursor.execute("""
    SELECT e.id, e.start_at, e.end_at, c.name, e.app_name, e.is_afk
    FROM events e
    LEFT JOIN categories c ON e.category_id = c.id
    WHERE LOWER(e.app_name) LIKE '%maya%'
    ORDER BY e.start_at DESC 
    LIMIT 30
""")
for row in cursor.fetchall():
    start = row[1][11:16] if row[1] else "?"
    end = row[2][11:16] if row[2] else "?"
    afk = "[AFK]" if row[5] else ""
    duration_sec = 0
    try:
        from datetime import datetime
        if row[1] and row[2]:
            start_dt = datetime.fromisoformat(row[1])
            end_dt = datetime.fromisoformat(row[2])
            duration_sec = int((end_dt - start_dt).total_seconds())
    except:
        pass
    print(f"ID:{row[0]:5d} | {start}~{end} ({duration_sec:4d}秒) | {row[3] or '未分類':12s} | {row[4]} {afk}")

print("\n" + "=" * 80)
print("カテゴリ別イベント集計 (今日)")
print("=" * 80)
cursor.execute("""
    SELECT c.name, COUNT(*) as event_count, SUM(
        CAST((julianday(e.end_at) - julianday(e.start_at)) * 86400 AS INTEGER)
    ) as total_seconds
    FROM events e
    LEFT JOIN categories c ON e.category_id = c.id
    WHERE date(e.start_at) = date('now', 'localtime')
    AND e.is_afk = 0
    GROUP BY c.id, c.name
    ORDER BY total_seconds DESC
""")
for row in cursor.fetchall():
    minutes = row[2] // 60 if row[2] else 0
    print(f"{row[0] or '未分類':15s} | {row[1]:4d}件 | {minutes:4d}分")

conn.close()
