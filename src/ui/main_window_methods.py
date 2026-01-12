
    def _show_settings(self) -> None:
        """設定ダイアログを表示"""
        from .settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(self)
        if dialog.exec():
            # 設定が保存されたらメッセージを表示
            QMessageBox.information(
                self, "設定保存完了",
                "設定を保存しました。\n一部の設定はアプリ再起動後に反映されます。"
            )
    
    def _update_status(self) -> None:
        """ステータスバーを更新"""
        if not self.afk_detector:
            return
        
        try:
            # アイドル時間
            idle_time = self.afk_detector.get_idle_time()
            if idle_time < 60:
                idle_str = f"{int(idle_time)}秒"
            else:
                minutes = int(idle_time / 60)
                seconds = int(idle_time % 60)
                idle_str = f"{minutes}分{seconds}秒"
            self.idle_time_label.setText(f"アイドル: {idle_str}")
            
            # AFK状態
            is_afk = self.afk_detector.is_afk()
            if is_afk:
                self.afk_status_label.setText("🔴 AFK")
                self.afk_status_label.setStyleSheet("color: red; font-weight: bold;")
            else:
                self.afk_status_label.setText("🟢 アクティブ")
                self.afk_status_label.setStyleSheet("color: green; font-weight: bold;")
            
            # セッション進捗（簡易版）
            from ..utils.config import get_config
            config = get_config()
            session_threshold = config.get("session_threshold", 10)
            
            # 現在のセッション時間を計算（簡易版：最新イベントから）
            latest_event = self.db.get_latest_event()
            if latest_event and not latest_event.get("is_afk"):
                from datetime import datetime
                start = latest_event.get("start_at")
                if isinstance(start, str):
                    start = datetime.fromisoformat(start)
                session_minutes = int((datetime.now() - start).total_seconds() / 60)
                self.session_progress_label.setText(f"セッション: {session_minutes}/{session_threshold}分")
            else:
                self.session_progress_label.setText(f"セッション: 0/{session_threshold}分")
        
        except Exception as e:
            print(f"ステータス更新エラー: {e}")
