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
        self.event_collector = EventCollector(self.db)
        self.window_monitor = WindowMonitor(
            interval=self.config.get("monitor_interval", 3),
            callback=self._on_window_change
        )
        
        # データ処理コンポーネント
        self.glue_engine = GlueEngine(self.db)
        self.session_detector = SessionDetector(self.db)
        
        # UI
        self.qt_app = None
        self.main_window = None
        self.system_tray = None
        
        # 定期処理用タイマー
        self.glue_timer = None
        self.session_timer = None
    
    def _on_window_change(self, window_info) -> None:
        """ウィンドウ変更時のコールバック"""
        is_afk = self.afk_detector.is_afk()
        self.event_collector.on_window_change(window_info, is_afk)
    
    def _process_glue_and_sessions(self) -> None:
        """定期的にGlueとセッション検出を実行"""
        try:
            # 最近24時間のイベントにGlueルールを適用
            self.glue_engine.process_recent_events(hours=24)
            
            # セッション検出と保存
            self.session_detector.process_and_save_sessions(hours=24)
        except Exception as e:
            print(f"Glue/セッション処理エラー: {e}")
    
    def start_background_services(self) -> None:
        """バックグラウンドサービスを開始"""
        print("バックグラウンドサービスを起動中...")
        
        # AFK検知開始
        self.afk_detector.start()
        
        # ウィンドウ監視開始
        self.window_monitor.start()
        
        # 定期処理タイマー(10分ごと)
        self.glue_timer = QTimer()
        self.glue_timer.timeout.connect(self._process_glue_and_sessions)
        self.glue_timer.start(10 * 60 * 1000)  # 10分 = 600,000ミリ秒
        
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
        self.main_window = MainWindow(self.db)
        
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
