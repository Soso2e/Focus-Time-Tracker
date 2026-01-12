"""
設定ダイアログ
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QSpinBox, QCheckBox, QGroupBox, QFormLayout, QTabWidget, QWidget,
    QMessageBox
)
from PySide6.QtCore import Qt

from ..utils.config import get_config, save_config


class SettingsDialog(QDialog):
    """設定ダイアログ"""
    
    def __init__(self, parent=None, db=None):
        super().__init__(parent)
        self.setWindowTitle("設定")
        self.setMinimumWidth(500)
        self.setMinimumHeight(450)
        
        self.config = get_config()
        self.db = db  # データベースインスタンス
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """UIをセットアップ"""
        layout = QVBoxLayout(self)
        
        # タブウィジェット
        tabs = QTabWidget()
        
        # 基本設定タブ
        basic_tab = self._create_basic_settings_tab()
        tabs.addTab(basic_tab, "基本設定")
        
        # 詳細設定タブ
        advanced_tab = self._create_advanced_settings_tab()
        tabs.addTab(advanced_tab, "詳細設定")
        
        # 通知設定タブ
        notification_tab = self._create_notification_settings_tab()
        tabs.addTab(notification_tab, "通知設定")
        
        # データ管理タブ
        if self.db:
            data_tab = self._create_data_management_tab()
            tabs.addTab(data_tab, "データ管理")
        
        layout.addWidget(tabs)
        
        # ボタン
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save_settings)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("キャンセル")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _create_basic_settings_tab(self) -> QWidget:
        """基本設定タブを作成"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # AFK閾値
        afk_group = QGroupBox("AFK（離席）検出")
        afk_layout = QFormLayout(afk_group)
        
        # AFK判定時間
        afk_threshold_layout = QHBoxLayout()
        self.afk_threshold_slider = QSlider(Qt.Horizontal)
        self.afk_threshold_slider.setMinimum(30)
        self.afk_threshold_slider.setMaximum(600)
        self.afk_threshold_slider.setValue(self.config.get("afk_threshold", 300))
        self.afk_threshold_slider.setTickPosition(QSlider.TicksBelow)
        self.afk_threshold_slider.setTickInterval(60)
        
        self.afk_threshold_spin = QSpinBox()
        self.afk_threshold_spin.setMinimum(30)
        self.afk_threshold_spin.setMaximum(600)
        self.afk_threshold_spin.setValue(self.config.get("afk_threshold", 300))
        self.afk_threshold_spin.setSuffix(" 秒")
        
        # スライダーとスピンボックスを同期
        self.afk_threshold_slider.valueChanged.connect(self.afk_threshold_spin.setValue)
        self.afk_threshold_spin.valueChanged.connect(self.afk_threshold_slider.setValue)
        
        afk_threshold_layout.addWidget(self.afk_threshold_slider)
        afk_threshold_layout.addWidget(self.afk_threshold_spin)
        
        afk_layout.addRow("AFK判定時間:", afk_threshold_layout)
        afk_layout.addRow("", QLabel("この時間操作がないとAFKとして記録"))
        
        # AFK警告閾値
        afk_warning_layout = QHBoxLayout()
        self.afk_warning_spin = QSpinBox()
        self.afk_warning_spin.setMinimum(10)
        self.afk_warning_spin.setMaximum(120)
        self.afk_warning_spin.setValue(self.config.get("afk_warning_threshold", 30))
        self.afk_warning_spin.setSuffix(" 秒")
        
        afk_warning_layout.addWidget(self.afk_warning_spin)
        afk_warning_layout.addStretch()
        
        afk_layout.addRow("AFK警告時間:", afk_warning_layout)
        afk_layout.addRow("", QLabel("AFK判定までこの時間で警告表示"))
        
        layout.addWidget(afk_group)
        
        # セッション閾値
        session_group = QGroupBox("集中セッション")
        session_layout = QFormLayout(session_group)
        
        # セッション認定時間
        session_threshold_layout = QHBoxLayout()
        self.session_threshold_slider = QSlider(Qt.Horizontal)
        self.session_threshold_slider.setMinimum(5)
        self.session_threshold_slider.setMaximum(60)
        self.session_threshold_slider.setValue(self.config.get("session_threshold", 10))
        self.session_threshold_slider.setTickPosition(QSlider.TicksBelow)
        self.session_threshold_slider.setTickInterval(5)
        
        self.session_threshold_spin = QSpinBox()
        self.session_threshold_spin.setMinimum(5)
        self.session_threshold_spin.setMaximum(60)
        self.session_threshold_spin.setValue(self.config.get("session_threshold", 10))
        self.session_threshold_spin.setSuffix(" 分")
        
        # 同期
        self.session_threshold_slider.valueChanged.connect(self.session_threshold_spin.setValue)
        self.session_threshold_spin.valueChanged.connect(self.session_threshold_slider.setValue)
        
        session_threshold_layout.addWidget(self.session_threshold_slider)
        session_threshold_layout.addWidget(self.session_threshold_spin)
        
        session_layout.addRow("セッション認定時間:", session_threshold_layout)
        session_layout.addRow("", QLabel("この時間連続作業でセッション獲得"))
        
        layout.addWidget(session_group)
        
        layout.addStretch()
        return widget
    
    def _create_advanced_settings_tab(self) -> QWidget:
        """詳細設定タブを作成"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 監視設定
        monitor_group = QGroupBox("監視設定")
        monitor_layout = QFormLayout(monitor_group)
        
        self.monitor_interval_spin = QSpinBox()
        self.monitor_interval_spin.setMinimum(1)
        self.monitor_interval_spin.setMaximum(10)
        self.monitor_interval_spin.setValue(self.config.get("monitor_interval", 3))
        self.monitor_interval_spin.setSuffix(" 秒")
        monitor_layout.addRow("ウィンドウ監視間隔:", self.monitor_interval_spin)
        
        self.high_cpu_threshold_spin = QSpinBox()
        self.high_cpu_threshold_spin.setMinimum(50)
        self.high_cpu_threshold_spin.setMaximum(100)
        self.high_cpu_threshold_spin.setValue(self.config.get("high_cpu_threshold", 80))
        self.high_cpu_threshold_spin.setSuffix(" %")
        monitor_layout.addRow("高CPU閾値:", self.high_cpu_threshold_spin)
        monitor_layout.addRow("", QLabel("この値以上のCPU使用率でスマートAFK無効"))
        
        layout.addWidget(monitor_group)
        
        layout.addStretch()
        return widget
    
    def _create_notification_settings_tab(self) -> QWidget:
        """通知設定タブを作成"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        notification_group = QGroupBox("通知設定")
        notification_layout = QVBoxLayout(notification_group)
        
        self.afk_notification_check = QCheckBox("AFK検出時に通知")
        self.afk_notification_check.setChecked(self.config.get("afk_notifications_enabled", True))
        notification_layout.addWidget(self.afk_notification_check)
        
        self.session_notification_check = QCheckBox("集中セッション獲得時に通知")
        self.session_notification_check.setChecked(self.config.get("session_notifications_enabled", True))
        notification_layout.addWidget(self.session_notification_check)
        
        # 通知テストボタン
        test_btn = QPushButton("通知をテスト")
        test_btn.clicked.connect(self._test_notification)
        notification_layout.addWidget(test_btn)
        
        layout.addWidget(notification_group)
        
        layout.addStretch()
        return widget
    
    def _test_notification(self) -> None:
        """通知をテスト"""
        from ..utils.notification import NotificationManager
        
        notifier = NotificationManager()
        notifier.notify_custom(
            "集中時間トラッカー",
            "通知テストが成功しました！"
        )
        
        QMessageBox.information(
            self,
            "通知テスト",
            "通知を送信しました。\n画面右下を確認してください。\n\n表示されない場合は、Windowsの通知設定を確認してください。"
        )
    
    def _create_data_management_tab(self) -> QWidget:
        """データ管理タブを作成"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # セッション再集計グループ
        session_group = QGroupBox("セッション管理")
        session_layout = QVBoxLayout(session_group)
        
        recalc_btn = QPushButton("セッションを再集計")
        recalc_btn.clicked.connect(self._recalculate_sessions)
        session_layout.addWidget(recalc_btn)
        
        session_layout.addWidget(QLabel("※既存のセッションを削除して再計算します"))
        
        layout.addWidget(session_group)
        
        # データ削除グループ
        data_group = QGroupBox("データ削除")
        data_layout = QVBoxLayout(data_group)
        
        # 今日のデータを削除
        delete_today_btn = QPushButton("今日のデータを削除")
        delete_today_btn.clicked.connect(self._delete_today_data)
        data_layout.addWidget(delete_today_btn)
        
        data_layout.addWidget(QLabel("※削除したデータは復元できません"))
        
        layout.addWidget(data_group)
        layout.addStretch()
        return widget
    
    def _delete_today_data(self) -> None:
        """今日のデータを削除"""
        if not self.db:
            return
        
        reply = QMessageBox.question(
            self,
            "確認",
            "今日のデータ（イベントとセッション）をすべて削除しますか?\n\nこの操作は取り消せません。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                events_deleted, sessions_deleted = self.db.delete_today_data()
                QMessageBox.information(
                    self,
                    "削除完了",
                    f"削除しました:\n  イベント: {events_deleted}件\n  セッション: {sessions_deleted}件"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "エラー",
                    f"削除に失敗しました: {e}"
                )
    
    def _recalculate_sessions(self) -> None:
        """セッションを再集計"""
        if not self.db:
            return
        
        reply = QMessageBox.question(
            self,
            "確認",
            "既存のセッションを削除して、イベントデータから再集計しますか?\n\nこの操作は取り消せません。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                from ..core.session_detector import SessionDetector
                from datetime import datetime, timedelta
                
                # 全セッションを削除
                deleted_count = self.db.delete_all_sessions()
                
                # 過去30日分のイベントを取得
                end_date = datetime.now()
                start_date = end_date - timedelta(days=30)
                events = self.db.get_events_by_date_range(start_date, end_date)
                
                # セッション検出
                detector = SessionDetector(self.db)
                sessions = detector.detect_sessions(events)
                
                # セッションを保存
                saved_count = 0
                for session in sessions:
                    self.db.add_session(
                        start_at=session["start_at"],
                        end_at=session["end_at"],
                        category_id=session["category_id"],
                        duration_minutes=session["duration_minutes"],
                        event_count=session["event_count"],
                        main_app_name=session.get("main_app_name")
                    )
                    saved_count += 1
                
                QMessageBox.information(
                    self,
                    "再集計完了",
                    f"セッションを再集計しました。\n削除: {deleted_count}件\n新規作成: {saved_count}件"
                )
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                print(f"セッション再集計エラー:\n{error_detail}")
                QMessageBox.critical(
                    self,
                    "エラー",
                    f"再集計に失敗しました:\n{str(e)}\n\n詳細はコンソールを確認してください。"
                )
    
    def _save_settings(self) -> None:
        """設定を保存"""
        new_config = {
            "afk_threshold": self.afk_threshold_spin.value(),
            "afk_warning_threshold": self.afk_warning_spin.value(),
            "session_threshold": self.session_threshold_spin.value(),
            "monitor_interval": self.monitor_interval_spin.value(),
            "high_cpu_threshold": self.high_cpu_threshold_spin.value(),
            "afk_notifications_enabled": self.afk_notification_check.isChecked(),
            "session_notifications_enabled": self.session_notification_check.isChecked(),
        }
        
        save_config(new_config)
        self.accept()
