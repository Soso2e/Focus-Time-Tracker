"""
メインアプリケーション
"""
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# PySide6のインポート
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
except ImportError:
    print("エラー: PySide6がインストールされていません")
    print("pip install PySide6 を実行してください")
    sys.exit(1)

# 内部モジュールのインポート
from src.data.database import Database
from src.core.monitor import WindowMonitor
from src.core.afk_detector import AFKDetector
from src.core.resource_monitor import ResourceMonitor
from src.core.event_collector import EventCollector
from src.core.glue_engine import GlueEngine
from src.core.session_detector import SessionDetector
from src.utils.config import get_config
from src.utils.notification import NotificationManager
from src.ui.main_window import MainWindow
from src.ui.system_tray import SystemTray


class FocusTrackerApp:
    """集中時間トラッカーアプリケーション"""
    
    def __init__(self):
        self.config = get_config()
        self.db = Database()
        self.db.initialize()
        
        # コアコンポーネント
        self.resource_monitor = ResourceMonitor(
            high_cpu_threshold=self.config.get("high_cpu_threshold", 80)
        )
        self.afk_detector = AFKDetector(
            threshold_seconds=self.config.get("afk_threshold", 300),
            resource_monitor=self.resource_monitor
        )
        
        # データ処理コンポーネント
        self.glue_engine = GlueEngine(self.db)
        
        # 通知マネージャー
        self.notification_manager = NotificationManager()
        
        # セッション検出器（通知マネージャーを渡す）
        self.session_detector = SessionDetector(self.db, self.notification_manager)
        
        # イベント収集器（セッション検出器を渡す）
        self.event_collector = EventCollector(self.db, self.session_detector)
        
        self.window_monitor = WindowMonitor(
            interval=self.config.get("monitor_interval", 3),
            callback=self._on_window_change
        )
        
        # UI
        self.qt_app = None
        self.main_window = None
        self.system_tray = None
        
        # 定期処理用タイマー
        self.glue_timer = None
        # Note: session_timerは削除（リアルタイム追跡に移行）
        
        # AFK状態の追跡
        self.was_afk = False
    
    def _on_window_change(self, window_info) -> None:
        """ウィンドウ変更時のコールバック"""
        self._check_afk_status()
        
        # AFK中は新しいイベントを記録しない
        if not self.was_afk:
            self.event_collector.on_window_change(window_info, False)
    
    def _check_afk_status(self) -> None:
        """AFK状態をチェックして記録"""
        is_afk = self.afk_detector.is_afk()
        idle_time = self.afk_detector.get_idle_time()
        
        # デバッグ情報
        if is_afk != self.was_afk:
            print(f"AFK状態変化: {self.was_afk} -> {is_afk} (アイドル時間: {idle_time:.1f}秒)")
        
        # AFK開始時
        if is_afk and not self.was_afk:
            print(f"AFK開始を検出 (アイドル時間: {idle_time:.1f}秒)")
            self.notification_manager.notify_afk_start()
            # 現在のイベントを終了（AFK開始時点で記録停止）
            self.event_collector.finalize_current_event()
        
        # AFK復帰時
        if not is_afk and self.was_afk:
            print("AFK復帰を検出")
            # 復帰時は次のウィンドウ変更で自動的に新しいイベントが開始される
        
        # アクティブ時は現在のイベントの終了時刻を更新（リアルタイム反映のため）
        if not is_afk and self.event_collector.current_event_id is not None:
            self.event_collector.update_current_event_end_time()
        
        self.was_afk = is_afk
        
        # UI更新（ステータスバーの時間を更新するため）
        if self.main_window:
            self.main_window.update_status()
    
    def _process_glue_and_sessions(self) -> None:
        """定期的にGlueとセッション検出を実行"""
        try:
            # 最近24時間のイベントにGlueルールを適用
            self.glue_engine.process_recent_events(hours=24)
            
            # セッション検出と保存 - リアルタイム追跡に移行したため無効化
            # self.session_detector.process_and_save_sessions(hours=24)
            print("[情報] セッション検出はリアルタイム追跡で行われます")
        except Exception as e:
            print(f"Glue処理エラー: {e}")
    
    def start_background_services(self) -> None:
        """バックグラウンドサービスを開始"""
        print("バックグラウンドサービスを起動中...")
        
        # AFK検知開始
        print(f"AFK検知を開始します (閾値: {self.afk_detector.threshold}秒)")
        self.afk_detector.start()
        
        # ウィンドウ監視開始
        self.window_monitor.start()
        
        # 定期処理タイマー(10分ごと)
        self.glue_timer = QTimer()
        self.glue_timer.timeout.connect(self._process_glue_and_sessions)
        self.glue_timer.start(10 * 60 * 1000)  # 10分 = 600,000ミリ秒
        
        # AFK状態チェックタイマー(30秒ごと)
        self.afk_check_timer = QTimer()
        self.afk_check_timer.timeout.connect(self._check_afk_status)
        self.afk_check_timer.start(30 * 1000)  # 30秒 = 30,000ミリ秒
        
        print("バックグラウンドサービスが起動しました")
    
    def stop_background_services(self) -> None:
        """バックグラウンドサービスを停止"""
        print("バックグラウンドサービスを停止中...")
        
        if self.glue_timer:
            self.glue_timer.stop()
        
        self.window_monitor.stop()
        self.afk_detector.stop()
        
        # 最後のイベントを終了
        self.event_collector.finalize_current_event()
        
        # データベース接続を閉じる
        self.db.close()
        
        print("バックグラウンドサービスを停止しました")
    
    def run(self) -> int:
        """アプリケーションを実行"""
        # Qt Applicationの初期化
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setQuitOnLastWindowClosed(False)  # トレイアイコンで常駐
        self.qt_app.setApplicationName("集中時間トラッカー")
        
        # メインウィンドウ
        self.main_window = MainWindow(self.db, self.afk_detector, self.session_detector)
        self.main_window.show()  # 起動時にウィンドウを表示
        
        # システムトレイ
        self.system_tray = SystemTray(self.main_window, self)
        self.system_tray.show()
        
        # バックグラウンドサービス開始
        self.start_background_services()
        
        # 終了時の処理
        self.qt_app.aboutToQuit.connect(self.stop_background_services)
        
        # アプリケーション実行
        return self.qt_app.exec()


def main():
    """エントリーポイント"""
    app = FocusTrackerApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
