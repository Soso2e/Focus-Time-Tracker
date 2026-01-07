"""
設定管理モジュール
"""
import json
import os
from pathlib import Path
from typing import Any, Dict


# デフォルト設定
DEFAULT_CONFIG = {
    "monitor_interval": 3,  # 秒
    "afk_threshold": 300,  # 秒(5分)
    "glue_tolerance": 180,  # 秒(3分)
    "session_threshold": 10,  # 分
    "save_window_titles": False,  # プライバシー重視
    "blacklist_apps": ["Bitwarden", "1Password", "KeePass", "LastPass"],
    "high_cpu_threshold": 80,  # CPU使用率(%)
}


class Config:
    """設定管理クラス"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            # デフォルトはdata/config.json
            base_dir = Path(__file__).parent.parent.parent
            config_path = base_dir / "data" / "config.json"
        
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.load()
    
    def load(self) -> None:
        """設定ファイルを読み込む"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                # デフォルト値で不足分を補完
                for key, value in DEFAULT_CONFIG.items():
                    if key not in self.config:
                        self.config[key] = value
            except Exception as e:
                print(f"設定ファイルの読み込みに失敗: {e}")
                self.config = DEFAULT_CONFIG.copy()
        else:
            # 設定ファイルが存在しない場合はデフォルトを使用
            self.config = DEFAULT_CONFIG.copy()
            self.save()
    
    def save(self) -> None:
        """設定ファイルに保存"""
        # ディレクトリが存在しない場合は作成
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"設定ファイルの保存に失敗: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """設定値を取得"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """設定値を更新"""
        self.config[key] = value
        self.save()
    
    def get_all(self) -> Dict[str, Any]:
        """すべての設定を取得"""
        return self.config.copy()
    
    def reset_to_default(self) -> None:
        """デフォルト設定にリセット"""
        self.config = DEFAULT_CONFIG.copy()
        self.save()


# グローバル設定インスタンス
_config_instance = None


def get_config() -> Config:
    """グローバル設定インスタンスを取得"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
