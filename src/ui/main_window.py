"""
メインウィンドウ(ダッシュボード)
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox, QMenu, QMessageBox, QDialog
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor

from ..data.database import Database
from .category_rule_widget import CategoryRuleWidget


class MainWindow(QMainWindow):
    """メインウィンドウ(ダッシュボード)"""
    
    def __init__(self, db: Database, afk_detector=None, session_detector=None):
        super().__init__()
        self.db = db
        self.afk_detector = afk_detector
        self.session_detector = session_detector
        
        self.current_period = "today"  # today, week, month
        
        self.setWindowTitle("集中時間トラッカー")
        self.setMinimumSize(1200, 700)
        
        # UI構築
        self._setup_ui()
        
        # データ読み込み
        self._load_data()
        
        # ステータスバー更新タイマー（30秒ごと）
        self.update_timer = QTimer(self) # Changed from self.status_timer to self.update_timer
        self.update_timer.timeout.connect(self._load_data) # Changed from _update_status to _load_data
        self.update_timer.start(30000)
        
        # ステータス更新タイマー(1秒ごと)
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(1000)
    
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
        
        # 設定ボタン
        settings_btn = QPushButton("⚙️ 設定")
        settings_btn.clicked.connect(self._show_settings)
        header_layout.addWidget(settings_btn)
        
        # 期間選択
        self.period_combo = QComboBox()
        self.period_combo.addItems(["今日", "今週", "今月"])
        self.period_combo.currentIndexChanged.connect(self._on_period_changed)
        header_layout.addWidget(QLabel("表示期間:"))
        header_layout.addWidget(self.period_combo)
        
        layout.addLayout(header_layout)
        
        # ステータスバー
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("ステータス:"))
        
        self.current_app_label = QLabel("アプリ: -")
        status_layout.addWidget(self.current_app_label)
        
        self.idle_time_label = QLabel("アイドル: 0秒")
        status_layout.addWidget(self.idle_time_label)
        
        self.afk_status_label = QLabel("🟢 アクティブ")
        status_layout.addWidget(self.afk_status_label)
        
        self.session_progress_label = QLabel("セッション: 0/10分")
        status_layout.addWidget(self.session_progress_label)
        
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
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
        self.category_table.cellDoubleClicked.connect(self._show_category_detail)
        tabs.addTab(self.category_table, "カテゴリ別")
        
        # アプリ別タブ
        self.app_table = QTableWidget()
        self.app_table.setColumnCount(5)
        self.app_table.setHorizontalHeaderLabels(["アプリ名", "プロセス名", "時間", "現在のカテゴリ", "カテゴリ変更"])
        self.app_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.app_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.app_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.app_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.app_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.app_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.app_table.customContextMenuRequested.connect(self._show_app_context_menu)
        tabs.addTab(self.app_table, "アプリ別")
        
        # セッションタブ
        self.session_table = QTableWidget()
        self.session_table.setColumnCount(6)
        self.session_table.setHorizontalHeaderLabels(["開始時刻", "終了時刻", "時間", "カウント", "カテゴリ", "メインアプリ"])
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
            # AFK イベントは作業時間から除外
            if event.get("is_afk", False):
                continue
            
            if event.get("start_at") and event.get("end_at"):
                start = datetime.fromisoformat(event["start_at"]) if isinstance(event["start_at"], str) else event["start_at"]
                end = datetime.fromisoformat(event["end_at"]) if isinstance(event["end_at"], str) else event["end_at"]
                total_time += (end - start).total_seconds()
        
        hours = int(total_time / 3600)
        minutes = int((total_time % 3600) / 60)
        
        # セッションカウントを10分マイルストーン数に変更
        milestone_count = sum(session.get("duration_minutes", 0) // 10 for session in sessions)
        
        period_text = {"today": "今日", "week": "今週", "month": "今月"}[self.current_period]
        
        summary = f"⏱️ {period_text}の作業時間: {hours}時間{minutes}分 | 🎯 集中セッション: {milestone_count}回"
        self.summary_label.setText(summary)
    
    def _update_category_table(self, events: List[Dict], sessions: List[Dict], categories: Dict) -> None:
        """カテゴリ別テーブルを更新"""
        # カテゴリごとの集計
        category_stats = {}
        total_time = 0
        
        for event in events:
            # AFK イベントは統計から除外
            if event.get("is_afk", False):
                continue
            
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
        
        # セッション数をカウント（マイルストーン数）
        for session in sessions:
            cat_id = session.get("category_id")
            if cat_id in category_stats:
                milestone_count = session.get("duration_minutes", 0) // 10
                category_stats[cat_id]["sessions"] += milestone_count
        
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
    
    def _show_category_detail(self, row: int, column: int) -> None:
        """カテゴリ詳細ダイアログを表示"""
        # カテゴリ名を取得
        category_name = self.category_table.item(row, 0).text()
        
        # カテゴリIDを取得
        categories = self.db.get_all_categories()
        category_id = None
        for cat in categories:
            if cat["name"] == category_name:
                category_id = cat["id"]
                break
        
        if not category_id:
            return
        
        # 期間を取得
        start_date, end_date = self._get_date_range()
        
        # このカテゴリのイベントを取得
        events = self.db.get_events_by_date_range(start_date, end_date)
        category_events = [e for e in events if e.get("category_id") == category_id]
        
        # アプリごとに集計
        app_stats = {}
        for event in category_events:
            if not event.get("start_at") or not event.get("end_at"):
                continue
            
            start = datetime.fromisoformat(event["start_at"]) if isinstance(event["start_at"], str) else event["start_at"]
            end = datetime.fromisoformat(event["end_at"]) if isinstance(event["end_at"], str) else event["end_at"]
            duration = (end - start).total_seconds()
            
            app_name = event.get("app_name", "不明")
            if app_name not in app_stats:
                app_stats[app_name] = 0
            app_stats[app_name] += duration
        
        # ダイアログを作成
        dialog = QDialog(self)
        dialog.setWindowTitle(f"カテゴリ詳細: {category_name}")
        dialog.setMinimumWidth(500)
        dialog.setMinimumHeight(400)
        
        layout = QVBoxLayout(dialog)
        
        # テーブル
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["アプリ名", "時間"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        
        # データを追加
        sorted_apps = sorted(app_stats.items(), key=lambda x: x[1], reverse=True)
        table.setRowCount(len(sorted_apps))
        
        for i, (app_name, duration) in enumerate(sorted_apps):
            table.setItem(i, 0, QTableWidgetItem(app_name))
            
            hours = int(duration / 3600)
            minutes = int((duration % 3600) / 60)
            table.setItem(i, 1, QTableWidgetItem(f"{hours}h {minutes}m"))
        
        layout.addWidget(table)
        
        # 閉じるボタン
        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.exec()
    
    def _update_app_table(self, events: List[Dict], categories: Dict) -> None:
        """アプリ別テーブルを更新"""
        # アプリ名（実行ファイル名）ごとに集計
        app_stats = {}
        
        for event in events:
            # AFK イベントは統計から除外
            if event.get("is_afk", False):
                continue
            
            if not event.get("start_at") or not event.get("end_at"):
                continue
            
            start = datetime.fromisoformat(event["start_at"]) if isinstance(event["start_at"], str) else event["start_at"]
            end = datetime.fromisoformat(event["end_at"]) if isinstance(event["end_at"], str) else event["end_at"]
            duration = (end - start).total_seconds()
            
            app_name = event.get("app_name", "不明")
            process_name = event.get("process_name", "不明")
            cat_id = event.get("category_id")
            
            # アプリ名をキーとして集計
            if app_name not in app_stats:
                app_stats[app_name] = {
                    "time": 0, 
                    "category_id": cat_id,
                    "app_name": app_name,
                    "process_names": set(),  # 複数のプロセス名を記録
                    "process_times": {}  # プロセス名ごとの時間を記録
                }
            app_stats[app_name]["time"] += duration
            app_stats[app_name]["process_names"].add(process_name)
            
            # プロセス名ごとの時間を集計
            if process_name not in app_stats[app_name]["process_times"]:
                app_stats[app_name]["process_times"][process_name] = 0
            app_stats[app_name]["process_times"][process_name] += duration
        
        # テーブル更新(トップ20)
        sorted_apps = sorted(app_stats.items(), key=lambda x: x[1]["time"], reverse=True)[:20]
        self.app_table.setRowCount(len(sorted_apps))
        
        # カテゴリリストを取得
        all_categories = self.db.get_all_categories()
        
        for row, (app_name, stats) in enumerate(sorted_apps):
            # アプリ名
            self.app_table.setItem(row, 0, QTableWidgetItem(stats["app_name"]))
            
            # プロセス名（常にボタンで表示）
            process_names_list = sorted(list(stats["process_names"]))
            if len(process_names_list) > 1:
                # 複数ある場合
                process_btn = QPushButton(f"{process_names_list[0]} 他{len(process_names_list)-1}件")
            else:
                # 1つだけの場合
                process_display = process_names_list[0] if process_names_list else "不明"
                process_btn = QPushButton(process_display)
            
            process_btn.clicked.connect(
                lambda checked, plist=process_names_list, a=app_name, pt=stats["process_times"]: 
                    self._show_process_list(plist, a, pt)
            )
            self.app_table.setCellWidget(row, 1, process_btn)
            
            # 時間
            hours = int(stats["time"] / 3600)
            minutes = int((stats["time"] % 3600) / 60)
            self.app_table.setItem(row, 2, QTableWidgetItem(f"{hours}h {minutes}m"))
            
            # 現在のカテゴリ（色付き）
            cat = categories.get(stats["category_id"], {"name": "不明", "color": "#CCCCCC"})
            cat_item = QTableWidgetItem(cat["name"])
            
            # カテゴリの色を反映
            if cat.get("color"):
                cat_item.setBackground(QColor(cat["color"]))
                # 背景色が暗い場合は白文字、明るい場合は黒文字
                color = QColor(cat["color"])
                if color.lightness() < 128:
                    cat_item.setForeground(QColor("#FFFFFF"))
                else:
                    cat_item.setForeground(QColor("#000000"))
            
            self.app_table.setItem(row, 3, cat_item)
            
            # カテゴリ変更用コンボボックス
            category_combo = QComboBox()
            category_combo.addItem("カテゴリを選択...", None)
            for category in all_categories:
                category_combo.addItem(category["name"], category)
            
            # コンボボックスの変更イベントを接続（アプリ名を使用）
            category_combo.currentIndexChanged.connect(
                lambda index, a=app_name, combo=category_combo: self._on_app_category_changed(a, combo)
            )
            
            self.app_table.setCellWidget(row, 4, category_combo)
    
    def _on_app_category_changed(self, app_name: str, combo: QComboBox) -> None:
        """アプリ別タブのカテゴリコンボボックス変更時の処理"""
        try:
            index = combo.currentIndex()
            if index <= 0:  # "カテゴリを選択..." が選ばれた場合
                return
            
            category = combo.itemData(index)
            if category:
                self._change_app_category(app_name, category)
                # コンボボックスを初期状態に戻す
                try:
                    combo.setCurrentIndex(0)
                except RuntimeError:
                    # コンボボックスが既に削除されている場合は無視
                    pass
        except RuntimeError:
            # コンボボックスが既に削除されている場合は無視
            pass
    
    def _show_process_list(self, process_names: List[str], app_name: str, process_times: Dict[str, float]) -> None:
        """プロセス名のリストをダイアログで表示"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{app_name} のプロセス一覧")
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(400)
        
        layout = QVBoxLayout(dialog)
        
        # 説明ラベル
        info_label = QLabel(
            f"「{app_name}」で検出されたプロセス（ウィンドウタイトル）の一覧です。\n"
            "特定のプロセスに異なるカテゴリを設定できます。"
        )
        layout.addWidget(info_label)
        
        # プロセスリストテーブル
        process_table = QTableWidget()
        process_table.setColumnCount(3)
        process_table.setHorizontalHeaderLabels(["プロセス名", "使用時間", "カテゴリ設定"])
        process_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        process_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        process_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        # プロセス名を使用時間でソート
        sorted_processes = sorted(process_names, key=lambda p: process_times.get(p, 0), reverse=True)
        process_table.setRowCount(len(sorted_processes))
        
        for row, process_name in enumerate(sorted_processes):
            # プロセス名
            process_table.setItem(row, 0, QTableWidgetItem(process_name))
            
            # 使用時間
            time_seconds = process_times.get(process_name, 0)
            hours = int(time_seconds / 3600)
            minutes = int((time_seconds % 3600) / 60)
            time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
            process_table.setItem(row, 1, QTableWidgetItem(time_str))
            
            # カテゴリ設定ボタン
            set_category_btn = QPushButton("カテゴリ設定")
            set_category_btn.clicked.connect(
                lambda checked, p=process_name: self._set_process_category(p, dialog)
            )
            process_table.setCellWidget(row, 2, set_category_btn)
        
        layout.addWidget(process_table)
        
        # 閉じるボタン
        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.exec()
    
    def _set_process_category(self, process_name: str, parent_dialog: QDialog) -> None:
        """特定のプロセスにカテゴリを設定"""
        # カテゴリ選択ダイアログ
        categories = self.db.get_all_categories()
        
        # メニューを作成
        menu = QMenu(self)
        for cat in categories:
            action = menu.addAction(cat["name"])
            action.triggered.connect(
                lambda checked, p=process_name, c=cat: self._change_process_category(p, c, parent_dialog)
            )
        
        # ダイアログの中央付近にメニューを表示
        menu.exec(parent_dialog.mapToGlobal(parent_dialog.rect().center()))
    
    def _change_process_category(self, process_name: str, category: Dict, parent_dialog: QDialog) -> None:
        """プロセス専用のカテゴリを設定"""
        reply = QMessageBox.question(
            self, "プロセス別カテゴリ設定",
            f"プロセス「{process_name}」を「{category['name']}」カテゴリに設定しますか？\n\n"
            f"このプロセス名のときのみ、アプリのカテゴリより優先して「{category['name']}」として分類されます。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # プロセス名ベースのルールを追加
                existing_rules = self.db.get_all_rules()
                rule_exists = any(
                    rule["match_target"] == "process" and 
                    rule["pattern"].lower() == process_name.lower()
                    for rule in existing_rules
                )
                
                if not rule_exists:
                    self.db.add_rule(
                        match_target="process",
                        pattern=process_name,
                        category_id=category["id"],
                        is_regex=False,
                        priority=20  # アプリ名より高い優先度
                    )
                    
                    # 過去のイベントも再分類するか確認
                    reclassify_reply = QMessageBox.question(
                        self, "過去のイベントを再分類",
                        f"ルールを登録しました。\n\n"
                        f"過去の「{process_name}」のイベントも「{category['name']}」に再分類しますか？",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    
                    if reclassify_reply == QMessageBox.Yes:
                        count = self.db.reclassify_events()
                        QMessageBox.information(
                            self, "完了",
                            f"{count}件のイベントを再分類しました。\n"
                            f"今後「{process_name}」は自動的に「{category['name']}」として分類されます。"
                        )
                    else:
                        QMessageBox.information(
                            self, "完了",
                            f"ルールを登録しました。\n今後「{process_name}」は自動的に「{category['name']}」として分類されます。"
                        )
                else:
                    QMessageBox.information(
                        self, "情報",
                        f"「{process_name}」のルールは既に存在します。\n設定タブから編集できます。"
                    )
                
                # データを再読み込み
                self._load_data()
                parent_dialog.accept()  # ダイアログを閉じる
                
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"ルール登録に失敗しました: {e}")
    
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
            
            # カウント（10分マイルストーン数）
            milestone_count = duration_min // 10
            count_item = QTableWidgetItem(f"{milestone_count}回")
            count_item.setTextAlignment(Qt.AlignCenter)
            self.session_table.setItem(row, 3, count_item)
            
            # カテゴリ（色付き）
            cat = categories.get(session.get("category_id"), {"name": "不明", "color": "#CCCCCC"})
            cat_item = QTableWidgetItem(cat["name"])
            
            # カテゴリの色を反映
            if cat.get("color"):
                cat_item.setBackground(QColor(cat["color"]))
                # 背景色が暗い場合は白文字、明るい場合は黒文字
                color = QColor(cat["color"])
                if color.lightness() < 128:
                    cat_item.setForeground(QColor("#FFFFFF"))
                else:
                    cat_item.setForeground(QColor("#000000"))
            
            self.session_table.setItem(row, 4, cat_item)
            
            # メインアプリ
            main_app = session.get("main_app_name", "不明")
            self.session_table.setItem(row, 5, QTableWidgetItem(main_app))
    
    def _show_app_context_menu(self, position) -> None:
        """アプリ別テーブルのコンテキストメニューを表示"""
        row = self.app_table.rowAt(position.y())
        if row < 0:
            return
        
        # アプリ名を取得（列0）
        app_name = self.app_table.item(row, 0).text()
        
        menu = QMenu(self)
        
        # カテゴリ変更サブメニュー
        change_category_menu = menu.addMenu(f"「{app_name}」のカテゴリを変更")
        
        categories = self.db.get_all_categories()
        for cat in categories:
            action = change_category_menu.addAction(cat["name"])
            action.triggered.connect(lambda checked, a=app_name, c=cat: self._change_app_category(a, c))
        
        # 削除オプション
        menu.addSeparator()
        delete_action = menu.addAction(f"「{app_name}」のデータを削除")
        delete_action.triggered.connect(lambda: self._delete_app_data(app_name))
        
        menu.exec(self.app_table.viewport().mapToGlobal(position))
    
    def _change_app_category(self, app_name: str, category: Dict) -> None:
        """アプリのカテゴリを変更し、ルールを登録（アプリ名ベース）"""
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
    
    def _delete_app_data(self, app_name: str) -> None:
        """アプリのデータを削除"""
        reply = QMessageBox.question(
            self,
            "確認",
            f"「{app_name}」のすべてのデータを削除しますか?\n\nこの操作は取り消せません。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                deleted_count = self.db.delete_events_by_app_name(app_name)
                QMessageBox.information(
                    self,
                    "削除完了",
                    f"「{app_name}」のデータを削除しました。\n削除されたイベント: {deleted_count}件"
                )
                # データを再読み込み
                self._load_data()
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "エラー",
                    f"削除に失敗しました: {e}"
                )
    
    def _show_settings(self) -> None:
        """設定ダイアログを表示"""
        from .settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(self, self.db)
        if dialog.exec():
            # 設定が保存されたらメッセージを表示
            QMessageBox.information(
                self, "設定保存完了",
                "設定を保存しました。\n一部の設定はアプリ再起動後に反映されます。"
            )
    
    def update_status(self) -> None:
        """ステータスバーを更新（外部呼び出し用）"""
        self._update_status()
    
    def _update_status(self) -> None:
        """ステータスバーを更新"""
        if not self.afk_detector:
            self.idle_time_label.setText("検出器なし")
            self.afk_status_label.setText("未接続")
            self.current_app_label.setText("アプリ: -")
            return
        
        try:
            # 設定を取得
            from ..utils.config import get_config
            config = get_config()
            
            # 現在のアプリ名を取得
            latest_event = self.db.get_latest_event()
            if latest_event and not latest_event.get("is_afk"):
                app_name = latest_event.get("app_name", "-")
                self.current_app_label.setText(f"アプリ: {app_name}")
            else:
                self.current_app_label.setText("アプリ: -")
            
            # アイドル時間（シンプル表示）
            idle_time = self.afk_detector.get_idle_time()
            afk_threshold = self.afk_detector.threshold
            afk_warning_threshold = config.get("afk_warning_threshold", 30)
            
            # AFK状態（シンプル表示）
            is_afk = self.afk_detector.is_afk()
            
            if is_afk:
                self.idle_time_label.setText("離席中")
                self.afk_status_label.setText("🔴 AFK")
                self.afk_status_label.setStyleSheet("""
                    color: white;
                    background-color: red;
                    font-weight: bold;
                    padding: 5px;
                    border-radius: 3px;
                """)
            else:
                remaining = int(afk_threshold - idle_time)
                if remaining < afk_warning_threshold:
                    # AFK間近
                    self.idle_time_label.setText(f"まもなくAFK")
                    self.afk_status_label.setText("🟡 警告")
                    self.afk_status_label.setStyleSheet("""
                        color: black;
                        background-color: yellow;
                        font-weight: bold;
                        padding: 5px;
                        border-radius: 3px;
                    """)
                else:
                    # アクティブ
                    if idle_time < 60:
                        self.idle_time_label.setText("作業中")
                    else:
                        minutes = int(idle_time / 60)
                        self.idle_time_label.setText(f"{minutes}分経過")
                    
                    self.afk_status_label.setText("🟢 アクティブ")
                    self.afk_status_label.setStyleSheet("""
                        color: white;
                        background-color: green;
                        font-weight: bold;
                        padding: 5px;
                        border-radius: 3px;
                    """)
            
            # セッション進捗（SessionDetectorから直接取得）
            session_threshold = config.get("session_threshold", 10)
            
            if self.session_detector and self.session_detector.active_session["app_name"]:
                # リアルタイムセッション状態から取得
                session_minutes = int(self.session_detector.active_session["accumulated_seconds"] / 60)
                
                if session_minutes >= session_threshold:
                    self.session_progress_label.setText(f"達成 ({session_minutes}分)")
                    self.session_progress_label.setStyleSheet("color: green; font-weight: bold;")
                else:
                    self.session_progress_label.setText(f"{session_minutes}/{session_threshold}分")
                    self.session_progress_label.setStyleSheet("")
            elif latest_event and not latest_event.get("is_afk"):
                # SessionDetectorがない場合のフォールバック（DBスキャン）
                from datetime import datetime, timedelta
                
                # 現在のアプリ名
                current_app = latest_event.get("app_name")
                
                # 過去1時間のイベントを取得
                end_date = datetime.now()
                start_date = end_date - timedelta(hours=1)
                recent_events = self.db.get_events_by_date_range(start_date, end_date)
                
                # 同じアプリの連続イベントを集計
                total_minutes = 0
                for event in reversed(recent_events):  # 新しい順
                    if event.get("is_afk"):
                        break  # AFKで中断
                    if event.get("app_name") != current_app:
                        break  # 異なるアプリで中断
                    
                    event_start = event.get("start_at")
                    event_end = event.get("end_at")
                    if event_start and event_end:
                        if isinstance(event_start, str):
                            event_start = datetime.fromisoformat(event_start)
                        if isinstance(event_end, str):
                            event_end = datetime.fromisoformat(event_end)
                        total_minutes += (event_end - event_start).total_seconds() / 60
                
                session_minutes = int(total_minutes)
                
                if session_minutes >= session_threshold:
                    self.session_progress_label.setText(f"達成 ({session_minutes}分)")
                    self.session_progress_label.setStyleSheet("color: green; font-weight: bold;")
                else:
                    self.session_progress_label.setText(f"{session_minutes}/{session_threshold}分")
                    self.session_progress_label.setStyleSheet("")
            else:
                self.session_progress_label.setText(f"0/{session_threshold}分")
                self.session_progress_label.setStyleSheet("")
        
        except Exception as e:
            print(f"ステータス更新エラー: {e}")
            import traceback
            traceback.print_exc()
