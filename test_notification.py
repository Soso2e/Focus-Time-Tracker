"""
通知テスト - Windows標準の通知を使用
"""
import subprocess
import sys

def test_windows_notification():
    """Windows標準の通知をテスト"""
    print("Windows標準通知をテスト中...")
    
    # PowerShellで通知を送信
    ps_script = """
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    [Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

    $template = @"
<toast>
    <visual>
        <binding template="ToastGeneric">
            <text>🎯 集中時間トラッカー</text>
            <text>テスト通知です！</text>
        </binding>
    </visual>
</toast>
"@

    $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
    $xml.LoadXml($template)
    $toast = New-Object Windows.UI.Notifications.ToastNotification $xml
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("集中時間トラッカー").Show($toast)
    """
    
    try:
        result = subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print("✅ Windows通知が送信されました！")
            return True
        else:
            print(f"❌ エラー: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 通知送信エラー: {e}")
        return False

def test_plyer_notification():
    """Plyer通知をテスト"""
    print("\nPlyer通知をテスト中...")
    
    try:
        from plyer import notification
        notification.notify(
            title="🎯 集中時間トラッカー",
            message="Plyerテスト通知です！",
            app_name="集中時間トラッカー",
            timeout=5
        )
        print("✅ Plyer通知が送信されました！")
        return True
    except ImportError:
        print("❌ Plyerがインストールされていません")
        return False
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("通知機能テスト")
    print("=" * 50)
    
    # Windows標準通知をテスト
    windows_ok = test_windows_notification()
    
    # Plyer通知をテスト
    plyer_ok = test_plyer_notification()
    
    print("\n" + "=" * 50)
    print("テスト結果:")
    print(f"  Windows通知: {'✅ OK' if windows_ok else '❌ NG'}")
    print(f"  Plyer通知:   {'✅ OK' if plyer_ok else '❌ NG'}")
    print("=" * 50)
    
    if not windows_ok and not plyer_ok:
        print("\n⚠️ どちらの通知も動作しませんでした")
        print("Windowsの通知設定を確認してください:")
        print("  設定 → システム → 通知")
    
    input("\nEnterキーを押して終了...")
