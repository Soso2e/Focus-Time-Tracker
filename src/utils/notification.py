"""
通知システム - Windows標準通知対応
"""
from datetime import datetime
from typing import Optional
import subprocess
import sys
import os

# plyerをオプショナルにする
PLYER_AVAILABLE = False
try:
    from plyer import notification
    PLYER_AVAILABLE = True
except ImportError:
    pass  # エラーを無視
except Exception as e:
    print(f"通知ライブラリの読み込みエラー: {e}")


class NotificationManager:
    """通知管理クラス"""
    
    def __init__(self):
        self.enabled = True  # 常に有効（Windows標準通知を使用）
        self.last_afk_notification = None
        self.last_session_notification = None
        self.use_windows_notification = sys.platform == "win32"
    
    def _send_windows_balloon(self, title: str, message: str) -> bool:
        """Windowsバルーン通知を送信（シンプル版）"""
        if not self.use_windows_notification:
            return False
        
        # PowerShellスクリプト（バルーン通知）
        ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
$notification = New-Object System.Windows.Forms.NotifyIcon
$notification.Icon = [System.Drawing.SystemIcons]::Information
$notification.BalloonTipTitle = "{title}"
$notification.BalloonTipText = "{message}"
$notification.Visible = $true
$notification.ShowBalloonTip(5000)
Start-Sleep -Seconds 2
$notification.Dispose()
"""
        
        try:
            # PowerShellを実行（ウィンドウを表示しない）
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                timeout=3,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            return result.returncode == 0
        except Exception as e:
            print(f"[通知エラー] {e}")
            return False
    
    def _send_windows_toast(self, title: str, message: str) -> bool:
        """Windowsトースト通知を送信"""
        if not self.use_windows_notification:
            return False
        
        # メッセージ内の改行をエスケープ
        message_escaped = message.replace("\n", "&#x0a;")
        
        ps_script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

$template = @"
<toast>
    <visual>
        <binding template="ToastGeneric">
            <text>{title}</text>
            <text>{message_escaped}</text>
        </binding>
    </visual>
</toast>
"@

$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)
$toast = New-Object Windows.UI.Notifications.ToastNotification $xml
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Python").Show($toast)
"""
        
        try:
            # PowerShellを実行（ウィンドウを表示しない）
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                timeout=3,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            return result.returncode == 0
        except Exception as e:
            print(f"[通知エラー] {e}")
            return False
    
    def _is_notification_enabled(self, notification_type: str) -> bool:
        """通知が有効かどうかをチェック"""
        if not self.enabled:
            return False
        
        try:
            from .config import get_config
            config = get_config()
            
            if notification_type == "afk":
                return config.get("afk_notifications_enabled", True)
            elif notification_type == "session":
                return config.get("session_notifications_enabled", True)
            
            return True
        except:
            return True  # 設定取得失敗時はデフォルトで有効
    
    def notify_afk_start(self) -> None:
        """AFK開始通知"""
        print("[通知] notify_afk_start が呼ばれました")
        
        if not self._is_notification_enabled("afk"):
            print("[通知] AFK通知は設定で無効になっています")
            return
        
        # 連続通知を防ぐ（1分以内は通知しない）
        now = datetime.now()
        if self.last_afk_notification and (now - self.last_afk_notification).total_seconds() < 60:
            print("[通知] AFK通知はスキップ（前回から1分以内）")
            return
        
        print("[通知] AFK通知を送信します...")
        
        # バルーン通知を試す（最も確実）
        print("[通知] バルーン通知を試行中...")
        if self._send_windows_balloon("離席を検出", "しばらく操作がありませんでした"):
            self.last_afk_notification = now
            print("[通知] バルーン通知送信成功")
            return
        
        # トースト通知を試す
        print("[通知] トースト通知を試行中...")
        if self._send_windows_toast("離席を検出", "しばらく操作がありませんでした"):
            self.last_afk_notification = now
            print("[通知] トースト通知送信成功")
            return
        
        # Plyerを試す
        if PLYER_AVAILABLE:
            print("[通知] Plyer通知を試行中...")
            try:
                notification.notify(
                    title="離席を検出",
                    message="しばらく操作がありませんでした",
                    app_name="集中時間トラッカー",
                    timeout=5
                )
                self.last_afk_notification = now
                print("[通知] Plyer通知送信成功")
            except:
                print("[通知] Plyer通知失敗")
        else:
            print("[通知] すべての通知方式が失敗しました")
    
    def notify_session_complete(self, duration_minutes: int, category_name: str, main_app: str) -> None:
        """集中セッション完了通知"""
        if not self._is_notification_enabled("session"):
            return
        
        # 連続通知を防ぐ（30秒以内は通知しない）
        now = datetime.now()
        if self.last_session_notification and (now - self.last_session_notification).total_seconds() < 30:
            return
        
        message = f"{duration_minutes}分間の集中セッションを達成！\nカテゴリ: {category_name}\nアプリ: {main_app}"
        
        # バルーン通知を試す（最も確実）
        if self._send_windows_balloon("集中セッション獲得", message):
            self.last_session_notification = now
            return
        
        # トースト通知を試す
        if self._send_windows_toast("集中セッション獲得", message):
            self.last_session_notification = now
            return
        
        # Plyerを試す
        if PLYER_AVAILABLE:
            try:
                notification.notify(
                    title="集中セッション獲得",
                    message=message,
                    app_name="集中時間トラッカー",
                    timeout=10
                )
                self.last_session_notification = now
            except:
                pass
    
    def notify_custom(self, title: str, message: str, timeout: int = 5) -> None:
        """カスタム通知"""
        if not self.enabled:
            return
        
        # バルーン通知を試す（最も確実）
        if self._send_windows_balloon(title, message):
            return
        
        # トースト通知を試す
        if self._send_windows_toast(title, message):
            return
        
        # Plyerを試す
        if PLYER_AVAILABLE:
            try:
                notification.notify(
                    title=title,
                    message=message,
                    app_name="集中時間トラッカー",
                    timeout=timeout
                )
                print("[通知] Plyer通知送信成功")
            except Exception as e:
                print(f"[通知エラー] Plyer: {e}")
