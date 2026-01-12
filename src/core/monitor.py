"""
アクティブウィンドウ監視モジュール
"""
import threading
import time
from datetime import datetime
from typing import Optional, Callable
from dataclasses import dataclass

try:
    import pywinctl as pwc
except ImportError:
    pwc = None
    print("警告: pywinctlがインストールされていません")


@dataclass
class WindowInfo:
    """ウィンドウ情報"""
    app_name: str
    process_name: Optional[str]
    window_title: Optional[str]
    timestamp: datetime


class WindowMonitor:
    """アクティブウィンドウ監視クラス"""
    
    def __init__(self, interval: int = 3, callback: Optional[Callable[[WindowInfo], None]] = None):
        """
        Args:
            interval: 監視間隔(秒)
            callback: ウィンドウ変更時のコールバック関数
        """
        self.interval = interval
        self.callback = callback
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.current_window: Optional[WindowInfo] = None
    
    def get_active_window(self) -> Optional[WindowInfo]:
        """現在のアクティブウィンドウ情報を取得"""
        if pwc is None:
            return None
        
        try:
            import psutil
        except ImportError:
            psutil = None
            print("警告: psutilがインストールされていません。プロセス情報の取得が制限されます。")
        
        try:
            window = pwc.getActiveWindow()
            if window is None:
                return None
            
            # アプリ名とプロセス名を取得
            app_name = None
            process_name = None
            exe_name = None
            
            if psutil:
                try:
                    # ウィンドウからプロセスIDを取得
                    if hasattr(window, '_hWnd'):
                        import win32process
                        import win32gui
                        _, pid = win32process.GetWindowThreadProcessId(window._hWnd)
                        
                        # プロセス情報を取得
                        process = psutil.Process(pid)
                        exe_name = process.name()  # 例: "Notion.exe"
                        
                        # アプリ名: 実行ファイル名から拡張子を除いたもの
                        app_name = exe_name.replace('.exe', '').replace('.EXE', '')
                    else:
                        # フォールバック: タイトルから推測
                        app_name = window.title.split(" - ")[-1] if window.title else "Unknown"
                except Exception as e:
                    print(f"プロセス情報取得エラー: {e}")
                    # フォールバック: タイトルから推測
                    app_name = window.title.split(" - ")[-1] if window.title else "Unknown"
            else:
                # psutilがない場合: タイトルから推測
                app_name = window.title.split(" - ")[-1] if window.title else "Unknown"
            
            # プロセス名: ウィンドウタイトルの最初の部分（" - "の前）
            if window.title:
                # " - " で分割して最初の部分を取得
                parts = window.title.split(" - ")
                if len(parts) > 1:
                    process_name = parts[0].strip()
                else:
                    # " - " がない場合はタイトル全体
                    process_name = window.title.strip()
            else:
                process_name = app_name
            
            return WindowInfo(
                app_name=app_name,
                process_name=process_name,
                window_title=window.title,
                timestamp=datetime.now()
            )
        except Exception as e:
            print(f"ウィンドウ情報取得エラー: {e}")
            return None
    
    def _monitor_loop(self) -> None:
        """監視ループ(バックグラウンドスレッド)"""
        while self.running:
            window_info = self.get_active_window()
            
            if window_info:
                # ウィンドウが変わった場合のみコールバックを呼ぶ
                if self.current_window is None or \
                   self.current_window.app_name != window_info.app_name or \
                   self.current_window.window_title != window_info.window_title:
                    
                    self.current_window = window_info
                    
                    if self.callback:
                        try:
                            self.callback(window_info)
                        except Exception as e:
                            print(f"コールバック実行エラー: {e}")
            
            time.sleep(self.interval)
    
    def start(self) -> None:
        """監視を開始"""
        if self.running:
            print("既に監視中です")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        print(f"ウィンドウ監視を開始しました(間隔: {self.interval}秒)")
    
    def stop(self) -> None:
        """監視を停止"""
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("ウィンドウ監視を停止しました")
    
    def set_callback(self, callback: Callable[[WindowInfo], None]) -> None:
        """コールバック関数を設定"""
        self.callback = callback
