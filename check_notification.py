"""
Windows通知設定チェックツール
"""
import subprocess
import sys

def check_windows_notification_settings():
    """Windows通知設定を確認"""
    print("=" * 60)
    print("Windows通知設定チェック")
    print("=" * 60)
    print()
    
    print("📋 通知設定を確認する方法:")
    print("  1. Windowsキー + I で設定を開く")
    print("  2. 「システム」→「通知」を選択")
    print("  3. 「通知」がオンになっているか確認")
    print("  4. 下にスクロールして「Python」または「PowerShell」の通知を確認")
    print()
    
    print("🔔 通知をテストします...")
    print()
    
    # テスト通知を送信
    ps_script = """
    Add-Type -AssemblyName System.Windows.Forms
    $notification = New-Object System.Windows.Forms.NotifyIcon
    $notification.Icon = [System.Drawing.SystemIcons]::Information
    $notification.BalloonTipTitle = "🎯 集中時間トラッカー"
    $notification.BalloonTipText = "通知テストが成功しました！"
    $notification.Visible = $true
    $notification.ShowBalloonTip(5000)
    Start-Sleep -Seconds 2
    $notification.Dispose()
    """
    
    try:
        print("方法1: バルーン通知を送信中...")
        result = subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print("✅ バルーン通知が送信されました！")
            print("   （タスクバーの右下を確認してください）")
        else:
            print(f"❌ エラー: {result.stderr}")
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    print()
    
    # Windows 10/11のトースト通知
    toast_script = """
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    [Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

    $template = @"
<toast>
    <visual>
        <binding template="ToastGeneric">
            <text>🎯 集中時間トラッカー</text>
            <text>トースト通知テストが成功しました！</text>
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
        print("方法2: トースト通知を送信中...")
        result = subprocess.run(
            ["powershell", "-Command", toast_script],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print("✅ トースト通知が送信されました！")
            print("   （画面右下を確認してください）")
        else:
            print(f"❌ エラー: {result.stderr}")
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    print()
    print("=" * 60)
    print("⚠️ 通知が表示されない場合:")
    print("=" * 60)
    print()
    print("1. 集中モードを確認:")
    print("   - タスクバー右下の通知アイコンをクリック")
    print("   - 「集中モード」がオフになっているか確認")
    print()
    print("2. 通知設定を確認:")
    print("   - 設定 → システム → 通知")
    print("   - 「アプリやその他の送信者からの通知を取得する」がオン")
    print("   - 「Python」の通知がオン")
    print()
    print("3. 通知設定を開く:")
    input("   Enterキーを押すと通知設定が開きます...")
    
    # 通知設定を開く
    try:
        subprocess.run(["start", "ms-settings:notifications"], shell=True)
    except:
        pass
    
    print()
    print("設定を確認したら、アプリを再起動してください。")

if __name__ == "__main__":
    check_windows_notification_settings()
    print()
    input("Enterキーを押して終了...")
