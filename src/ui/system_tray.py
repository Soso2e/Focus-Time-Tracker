"""
システムトレイアイコン
"""
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QSize
import sys


class SystemTray(QSystemTrayIcon):
    """システムトレイアイコン"""
    
    def __init__(self, main_window, app):
        # アイコンを作成(簡易的にデフォルトアイコンを使用)
        super().__init__()
        
        self.main_window = main_window
        self.app = app
        
        # ツールチップ
        self.setToolTip("集中時間トラッカー")
        
        # コンテキストメニュー
        menu = QMenu()
        
        # ダッシュボードを開く
        show_action = QAction("📊 ダッシュボードを開く", menu)
        show_action.triggered.connect(self.show_dashboard)
        menu.addAction(show_action)
        
        menu.addSeparator()
        
        # 一時停止/再開
        self.pause_action = QAction("⏸️ 一時停止", menu)
        self.pause_action.triggered.connect(self.toggle_pause)
        menu.addAction(self.pause_action)
        
        menu.addSeparator()
        
        # 終了
        quit_action = QAction("❌ 終了", menu)
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(quit_action)
        
        self.setContextMenu(menu)
        
        # ダブルクリックでダッシュボードを開く
        self.activated.connect(self.on_activated)
        
        self.is_paused = False
    
    def on_activated(self, reason):
        """トレイアイコンクリック時"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_dashboard()
    
    def show_dashboard(self):
        """ダッシュボードを表示"""
        self.main_window.show()
        self.main_window.activateWindow()
        self.main_window.raise_()
    
    def toggle_pause(self):
        """一時停止/再開を切り替え"""
        if self.is_paused:
            # 再開
            self.app.start_background_services()
            self.pause_action.setText("⏸️ 一時停止")
            self.setToolTip("集中時間トラッカー (実行中)")
            self.is_paused = False
        else:
            # 一時停止
            self.app.stop_background_services()
            self.pause_action.setText("▶️ 再開")
            self.setToolTip("集中時間トラッカー (一時停止中)")
            self.is_paused = True
    
    def quit_app(self):
        """アプリケーションを終了"""
        self.app.qt_app.quit()
