"""
メインウィンドウ(ダッシュボード)
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox, QMenu, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor

from ..data.database import Database
from .category_rule_widget import CategoryRuleWidget


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
        self.summary_label.setStyleSheet("""
            font-size: 14px; 
            padding: 10px; 
            background-color: palette(alternate-base); 
            border-radius: 5px;
            color: palette(text);
        """)
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
        self.app_table.setColumnCount(4)
        self.app_table.setHorizontalHeaderLabels(["アプリ", "時間", "現在のカテゴリ", "カテゴリ変更"])
        self.app_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.app_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.app_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.app_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.app_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.app_table.customContextMenuRequested.connect(self._show_app_context_menu)
        tabs.addTab(self.app_table, "アプリ別")
        
        # セッションタブ
        self.session_table = QTableWidget()
        self.session_table.setColumnCount(4)
        self.session_table.setHorizontalHeaderLabels(["開始時刻", "終了時刻", "時間", "カテゴリ"])
        self.session_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tabs.addTab(self.session_table, "集中セッション")
        
        # カテゴリ・ルール設定タブ
        self.category_rule_widget = CategoryRuleWidget(self.db)
        self.category_rule_widget.data_changed.connect(self._load_data)  # 設定変更時にデータ再読み込み
        tabs.addTab(self.category_rule_widget, "⚙️ 設定")
        
        layout.addWidget(tabs)
        
        # フッター
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        
        # イベント再分類ボタン
        reclassify_btn = QPushButton("🔄 イベント再分類")
        reclassify_btn.setToolTip("現在の期間のイベントを最新のルールで再分類します")
        reclassify_btn.clicked.connect(self._reclassify_events)
        footer_layout.addWidget(reclassify_btn)
        
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
    
    def _reclassify_events(self) -> None:
        """現在の期間のイベントを再分類"""
        reply = QMessageBox.question(
            self, "イベント再分類",
            "現在表示されている期間のイベントを最新のルールで再分類しますか？\n\n"
            "この操作により、過去のイベントのカテゴリが変更される可能性があります。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                start_date, end_date = self._get_date_range()
                count = self.db.reclassify_events(start_date, end_date)
                
                QMessageBox.information(
                    self, "完了",
                    f"{count}件のイベントを再分類しました。"
                )
                
                # データを再読み込み
                self._load_data()
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"再分類に失敗しました: {e}")
    
    def _load_data(self) -> None:
        """データを読み込んで表示"""
        try:
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
        except Exception as e:
            print(f"データ読み込みエラー: {e}")
            # エラーが発生してもアプリケーションは継続
    
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
                # 背景色が暗い場合は白文字、明るい場合は黒文字
                color = QColor(cat["color"])
                if color.lightness() < 128:
                    name_item.setForeground(QColor("#FFFFFF"))
                else:
                    name_item.setForeground(QColor("#000000"))
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
        
        # カテゴリリストを取得
        all_categories = self.db.get_all_categories()
        
        for row, (app_name, stats) in enumerate(sorted_apps):
            # アプリ名
            self.app_table.setItem(row, 0, QTableWidgetItem(app_name))
            
            # 時間
            hours = int(stats["time"] / 3600)
            minutes = int((stats["time"] % 3600) / 60)
            self.app_table.setItem(row, 1, QTableWidgetItem(f"{hours}h {minutes}m"))
            
            # 現在のカテゴリ
            cat = categories.get(stats["category_id"], {"name": "不明"})
            self.app_table.setItem(row, 2, QTableWidgetItem(cat["name"]))
            
            # カテゴリ変更用コンボボックス
            category_combo = QComboBox()
            category_combo.addItem("カテゴリを選択...", None)
            for category in all_categories:
                category_combo.addItem(category["name"], category)
            
            # コンボボックスの変更イベントを接続
            category_combo.currentIndexChanged.connect(
                lambda index, a=app_name, combo=category_combo: self._on_app_category_changed(a, combo)
            )
            
            self.app_table.setCellWidget(row, 3, category_combo)
    
    def _on_app_category_changed(self, app_name: str, combo: QComboBox) -> None:
        """アプリ別タブのカテゴリコンボボックス変更時の処理"""
        index = combo.currentIndex()
        if index <= 0:  # "カテゴリを選択..." が選ばれた場合
            return
        
        category = combo.itemData(index)
        if category:
            self._change_app_category(app_name, category)
            # コンボボックスを初期状態に戻す
            combo.setCurrentIndex(0)
    
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
    
    def _show_app_context_menu(self, position) -> None:
        """アプリ別テーブルのコンテキストメニューを表示"""
        row = self.app_table.rowAt(position.y())
        if row < 0:
            return
        
        app_name = self.app_table.item(row, 0).text()
        
        menu = QMenu(self)
        
        # カテゴリ変更サブメニュー
        change_category_menu = menu.addMenu(f"「{app_name}」のカテゴリを変更")
        
        categories = self.db.get_all_categories()
        for cat in categories:
            action = change_category_menu.addAction(cat["name"])
            action.triggered.connect(lambda checked, a=app_name, c=cat: self._change_app_category(a, c))
        
        menu.exec(self.app_table.viewport().mapToGlobal(position))
    
    def _change_app_category(self, app_name: str, category: Dict) -> None:
        """アプリのカテゴリを変更し、ルールを登録"""
        # 確認ダイアログ
        reply = QMessageBox.question(
            self, "カテゴリ変更とルール登録",
            f"「{app_name}」を「{category['name']}」カテゴリに変更しますか？\n\n"
            f"今後このアプリを自動的に「{category['name']}」として分類するルールも登録されます。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # ルールを追加（既存のルールと重複しないようチェック）
                existing_rules = self.db.get_all_rules()
                rule_exists = any(
                    rule["match_target"] == "app_name" and 
                    rule["pattern"].lower() == app_name.lower()
                    for rule in existing_rules
                )
                
                if not rule_exists:
                    self.db.add_rule(
                        match_target="app_name",
                        pattern=app_name,
                        category_id=category["id"],
                        is_regex=False,
                        priority=10
                    )
                    
                    # 過去のイベントも再分類するか確認
                    reclassify_reply = QMessageBox.question(
                        self, "過去のイベントを再分類",
                        f"ルールを登録しました。\n\n"
                        f"過去の「{app_name}」のイベントも「{category['name']}」に再分類しますか？",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    
                    if reclassify_reply == QMessageBox.Yes:
                        # 全期間のイベントを再分類
                        count = self.db.reclassify_events()
                        QMessageBox.information(
                            self, "完了",
                            f"{count}件のイベントを再分類しました。\n"
                            f"今後「{app_name}」は自動的に「{category['name']}」として分類されます。"
                        )
                    else:
                        QMessageBox.information(
                            self, "完了",
                            f"ルールを登録しました。\n今後「{app_name}」は自動的に「{category['name']}」として分類されます。"
                        )
                else:
                    QMessageBox.information(
                        self, "情報",
                        f"「{app_name}」のルールは既に存在します。\n設定タブから編集できます。"
                    )
                
                # データを再読み込み
                self._load_data()
                
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"ルール登録に失敗しました: {e}")
