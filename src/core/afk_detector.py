"""
AFK(離席)検知モジュール
"""
import threading
import time
from datetime import datetime, timedelta
from typing import Optional

try:
    from pynput import keyboard, mouse
except ImportError:
    keyboard = None
    mouse = None
    print("警告: pynputがインストールされていません")

from .resource_monitor import ResourceMonitor


class AFKDetector:
    """AFK検知クラス"""
    
    def __init__(self, threshold_seconds: int = 300, resource_monitor: Optional[ResourceMonitor] = None):
        """
        Args:
            threshold_seconds: AFK判定のしきい値(秒)
            resource_monitor: リソース監視インスタンス(スマートAFK用)
        """
        self.threshold = threshold_seconds
        self.resource_monitor = resource_monitor or ResourceMonitor()
        self.last_activity = datetime.now()
        self.running = False
        self.keyboard_listener: Optional[keyboard.Listener] = None
        self.mouse_listener: Optional[mouse.Listener] = None
    
    def _on_activity(self) -> None:
        """入力アクティビティ発生時のコールバック"""
        self.last_activity = datetime.now()
    
    def _on_key_press(self, key) -> None:
        """キーボード押下時"""
        self._on_activity()
    
    def _on_mouse_move(self, x, y) -> None:
        """マウス移動時"""
        self._on_activity()
    
    def _on_mouse_click(self, x, y, button, pressed) -> None:
        """マウスクリック時"""
        if pressed:
            self._on_activity()
    
    def _on_mouse_scroll(self, x, y, dx, dy) -> None:
        """マウススクロール時"""
        self._on_activity()
    
    def get_idle_time(self) -> float:
        """
        アイドル時間を取得(秒)
        
        Returns:
            最終アクティビティからの経過時間(秒)
        """
        return (datetime.now() - self.last_activity).total_seconds()
    
    def is_afk(self) -> bool:
        """
        AFK状態かどうかを判定(スマートAFK対応)
        
        Returns:
            True: AFK, False: アクティブ
        """
        idle_time = self.get_idle_time()
        
        # しきい値未満ならアクティブ
        if idle_time < self.threshold:
            return False
        
        # スマートAFK: 高負荷時(レンダリング中など)はAFKとしない
        try:
            if self.resource_monitor.is_high_load():
                return False
        except:
            pass
        
        return True
    
    def start(self) -> None:
        """入力監視を開始"""
        if self.running:
            print("既に監視中です")
            return
        
        if keyboard is None or mouse is None:
            print("エラー: pynputがインストールされていません")
            return
        
        self.running = True
        self.last_activity = datetime.now()
        
        # キーボードリスナー
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press
        )
        self.keyboard_listener.start()
        
        # マウスリスナー
        self.mouse_listener = mouse.Listener(
            on_move=self._on_mouse_move,
            on_click=self._on_mouse_click,
            on_scroll=self._on_mouse_scroll
        )
        self.mouse_listener.start()
        
        print(f"AFK検知を開始しました(しきい値: {self.threshold}秒)")
    
    def stop(self) -> None:
        """入力監視を停止"""
        if not self.running:
            return
        
        self.running = False
        
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            self.keyboard_listener = None
        
        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener = None
        
        print("AFK検知を停止しました")
