"""
メインウィンドウ(ダッシュボード)
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor

from ..data.database import Database


class MainWindow(QMainWindow):
    """メインウィンドウ(ダッシュボード)"""
    
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.current_period = "today"  # today, week, month
        
        self.setWindowTitle("集中時間トラッカー")
        self.setMinimumSize(900, 600)
        
        self._setup_ui()
        self._load_data()
        
        # 定期更新タイマー(30秒ごと)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._load_data)
        self.update_timer.start(30000)
    
    def _setup_ui(self) -> None:
        """UIをセットアップ"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # ヘッダー
        header_layout = QHBoxLayout()
        title_label = QLabel("📊 集中時間トラッカー")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # 期間選択
        self.period_combo = QComboBox()
        self.period_combo.addItems(["今日", "今週", "今月"])
        self.period_combo.currentIndexChanged.connect(self._on_period_changed)
        header_layout.addWidget(QLabel("表示期間:"))
        header_layout.addWidget(self.period_combo)
        
        layout.addLayout(header_layout)
        
        # 統計サマリー
        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("font-size: 14px; padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        layout.addWidget(self.summary_label)
        
        # タブ
        tabs = QTabWidget()
        
        # カテゴリ別タブ
        self.category_table = QTableWidget()
        self.category_table.setColumnCount(4)
        self.category_table.setHorizontalHeaderLabels(["カテゴリ", "時間", "割合", "セッション数"])
        self.category_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tabs.addTab(self.category_table, "カテゴリ別")
        
        # アプリ別タブ
        self.app_table = QTableWidget()
        self.app_table.setColumnCount(3)
        self.app_table.setHorizontalHeaderLabels(["アプリ", "時間", "カテゴリ"])
        self.app_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tabs.addTab(self.app_table, "アプリ別")
        
        # セッションタブ
        self.session_table = QTableWidget()
        self.session_table.setColumnCount(4)
        self.session_table.setHorizontalHeaderLabels(["開始時刻", "終了時刻", "時間", "カテゴリ"])
        self.session_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tabs.addTab(self.session_table, "集中セッション")
        
        layout.addWidget(tabs)
        
        # フッター
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        refresh_btn = QPushButton("🔄 更新")
        refresh_btn.clicked.connect(self._load_data)
        footer_layout.addWidget(refresh_btn)
        
        layout.addLayout(footer_layout)
    
    def _on_period_changed(self, index: int) -> None:
        """期間選択変更時"""
        periods = ["today", "week", "month"]
        self.current_period = periods[index]
        self._load_data()
    
    def _get_date_range(self) -> tuple:
        """現在の期間に応じた日付範囲を取得"""
        now = datetime.now()
        
        if self.current_period == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif self.current_period == "week":
            # 今週の月曜日から
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        else:  # month
            # 今月の1日から
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now
        
        return start, end
    
    def _load_data(self) -> None:
        """データを読み込んで表示"""
        start_date, end_date = self._get_date_range()
        
        # イベント取得
        events = self.db.get_events_by_date_range(start_date, end_date)
        
        # セッション取得
        sessions = self.db.get_sessions_by_date_range(start_date, end_date)
        
        # カテゴリ情報取得
        categories = {cat["id"]: cat for cat in self.db.get_all_categories()}
        
        # 統計計算
        self._update_summary(events, sessions)
        self._update_category_table(events, sessions, categories)
        self._update_app_table(events, categories)
        self._update_session_table(sessions, categories)
    
    def _update_summary(self, events: List[Dict], sessions: List[Dict]) -> None:
        """サマリーを更新"""
        total_time = 0
        for event in events:
            if event.get("start_at") and event.get("end_at"):
                start = datetime.fromisoformat(event["start_at"]) if isinstance(event["start_at"], str) else event["start_at"]
                end = datetime.fromisoformat(event["end_at"]) if isinstance(event["end_at"], str) else event["end_at"]
                total_time += (end - start).total_seconds()
        
        hours = int(total_time / 3600)
        minutes = int((total_time % 3600) / 60)
        
        session_count = len(sessions)
        
        period_text = {"today": "今日", "week": "今週", "month": "今月"}[self.current_period]
        
        summary = f"⏱️ {period_text}の作業時間: {hours}時間{minutes}分 | 🎯 集中セッション: {session_count}回"
        self.summary_label.setText(summary)
    
    def _update_category_table(self, events: List[Dict], sessions: List[Dict], categories: Dict) -> None:
        """カテゴリ別テーブルを更新"""
        # カテゴリごとの集計
        category_stats = {}
        total_time = 0
        
        for event in events:
            if not event.get("start_at") or not event.get("end_at"):
                continue
            
            start = datetime.fromisoformat(event["start_at"]) if isinstance(event["start_at"], str) else event["start_at"]
            end = datetime.fromisoformat(event["end_at"]) if isinstance(event["end_at"], str) else event["end_at"]
            duration = (end - start).total_seconds()
            total_time += duration
            
            cat_id = event.get("category_id")
            if cat_id not in category_stats:
                category_stats[cat_id] = {"time": 0, "sessions": 0}
            category_stats[cat_id]["time"] += duration
        
        # セッション数をカウント
        for session in sessions:
            cat_id = session.get("category_id")
            if cat_id in category_stats:
                category_stats[cat_id]["sessions"] += 1
        
        # テーブル更新
        self.category_table.setRowCount(len(category_stats))
        
        for row, (cat_id, stats) in enumerate(sorted(category_stats.items(), key=lambda x: x[1]["time"], reverse=True)):
            cat = categories.get(cat_id, {"name": "不明", "color": "#CCCCCC"})
            
            # カテゴリ名
            name_item = QTableWidgetItem(cat["name"])
            if cat.get("color"):
                name_item.setBackground(QColor(cat["color"]))
            self.category_table.setItem(row, 0, name_item)
            
            # 時間
            hours = int(stats["time"] / 3600)
            minutes = int((stats["time"] % 3600) / 60)
            time_item = QTableWidgetItem(f"{hours}h {minutes}m")
            self.category_table.setItem(row, 1, time_item)
            
            # 割合
            percentage = (stats["time"] / total_time * 100) if total_time > 0 else 0
            percent_item = QTableWidgetItem(f"{percentage:.1f}%")
            self.category_table.setItem(row, 2, percent_item)
            
            # セッション数
            session_item = QTableWidgetItem(str(stats["sessions"]))
            self.category_table.setItem(row, 3, session_item)
    
    def _update_app_table(self, events: List[Dict], categories: Dict) -> None:
        """アプリ別テーブルを更新"""
        # アプリごとの集計
        app_stats = {}
        
        for event in events:
            if not event.get("start_at") or not event.get("end_at"):
                continue
            
            start = datetime.fromisoformat(event["start_at"]) if isinstance(event["start_at"], str) else event["start_at"]
            end = datetime.fromisoformat(event["end_at"]) if isinstance(event["end_at"], str) else event["end_at"]
            duration = (end - start).total_seconds()
            
            app_name = event.get("app_name", "不明")
            cat_id = event.get("category_id")
            
            if app_name not in app_stats:
                app_stats[app_name] = {"time": 0, "category_id": cat_id}
            app_stats[app_name]["time"] += duration
        
        # テーブル更新(トップ20)
        sorted_apps = sorted(app_stats.items(), key=lambda x: x[1]["time"], reverse=True)[:20]
        self.app_table.setRowCount(len(sorted_apps))
        
        for row, (app_name, stats) in enumerate(sorted_apps):
            # アプリ名
            self.app_table.setItem(row, 0, QTableWidgetItem(app_name))
            
            # 時間
            hours = int(stats["time"] / 3600)
            minutes = int((stats["time"] % 3600) / 60)
            self.app_table.setItem(row, 1, QTableWidgetItem(f"{hours}h {minutes}m"))
            
            # カテゴリ
            cat = categories.get(stats["category_id"], {"name": "不明"})
            self.app_table.setItem(row, 2, QTableWidgetItem(cat["name"]))
    
    def _update_session_table(self, sessions: List[Dict], categories: Dict) -> None:
        """セッションテーブルを更新"""
        self.session_table.setRowCount(len(sessions))
        
        for row, session in enumerate(reversed(sessions)):  # 新しい順
            # 開始時刻
            start = session.get("start_at")
            if isinstance(start, str):
                start = datetime.fromisoformat(start)
            start_str = start.strftime("%m/%d %H:%M") if start else "-"
            self.session_table.setItem(row, 0, QTableWidgetItem(start_str))
            
            # 終了時刻
            end = session.get("end_at")
            if isinstance(end, str):
                end = datetime.fromisoformat(end)
            end_str = end.strftime("%H:%M") if end else "-"
            self.session_table.setItem(row, 1, QTableWidgetItem(end_str))
            
            # 時間
            duration_min = session.get("duration_minutes", 0)
            hours = duration_min // 60
            minutes = duration_min % 60
            time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
            self.session_table.setItem(row, 2, QTableWidgetItem(time_str))
            
            # カテゴリ
            cat = categories.get(session.get("category_id"), {"name": "不明"})
            self.session_table.setItem(row, 3, QTableWidgetItem(cat["name"]))
