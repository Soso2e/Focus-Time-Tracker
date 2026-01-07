"""
デフォルトカテゴリとルール
"""

# デフォルトカテゴリ(クリエイター向け)
DEFAULT_CATEGORIES = [
    {"name": "3D制作", "color": "#FF6B6B", "is_productive": True},
    {"name": "映像編集", "color": "#4ECDC4", "is_productive": True},
    {"name": "ゲーム開発", "color": "#45B7D1", "is_productive": True},
    {"name": "コーディング", "color": "#96CEB4", "is_productive": True},
    {"name": "資料・設計", "color": "#FFEAA7", "is_productive": True},
    {"name": "調べ物", "color": "#DFE6E9", "is_productive": True},
    {"name": "連絡", "color": "#74B9FF", "is_productive": False},
    {"name": "休憩", "color": "#A29BFE", "is_productive": False},
    {"name": "未分類", "color": "#B2BEC3", "is_productive": False},
]

# デフォルト分類ルール
DEFAULT_RULES = [
    # 3D制作
    {"pattern": "Maya", "match_target": "app_name", "category": "3D制作", "is_regex": False, "priority": 10},
    {"pattern": "Blender", "match_target": "app_name", "category": "3D制作", "is_regex": False, "priority": 10},
    {"pattern": "3ds Max", "match_target": "app_name", "category": "3D制作", "is_regex": False, "priority": 10},
    {"pattern": "Cinema 4D", "match_target": "app_name", "category": "3D制作", "is_regex": False, "priority": 10},
    {"pattern": "Houdini", "match_target": "app_name", "category": "3D制作", "is_regex": False, "priority": 10},
    
    # 映像編集
    {"pattern": "After Effects", "match_target": "app_name", "category": "映像編集", "is_regex": False, "priority": 10},
    {"pattern": "Premiere", "match_target": "app_name", "category": "映像編集", "is_regex": False, "priority": 10},
    {"pattern": "DaVinci Resolve", "match_target": "app_name", "category": "映像編集", "is_regex": False, "priority": 10},
    {"pattern": "Final Cut", "match_target": "app_name", "category": "映像編集", "is_regex": False, "priority": 10},
    
    # ゲーム開発
    {"pattern": "Unity", "match_target": "app_name", "category": "ゲーム開発", "is_regex": False, "priority": 10},
    {"pattern": "Unreal", "match_target": "app_name", "category": "ゲーム開発", "is_regex": False, "priority": 10},
    {"pattern": "Godot", "match_target": "app_name", "category": "ゲーム開発", "is_regex": False, "priority": 10},
    
    # コーディング
    {"pattern": "Code", "match_target": "app_name", "category": "コーディング", "is_regex": False, "priority": 10},
    {"pattern": "Visual Studio", "match_target": "app_name", "category": "コーディング", "is_regex": False, "priority": 10},
    {"pattern": "PyCharm", "match_target": "app_name", "category": "コーディング", "is_regex": False, "priority": 10},
    {"pattern": "IntelliJ", "match_target": "app_name", "category": "コーディング", "is_regex": False, "priority": 10},
    {"pattern": "Sublime", "match_target": "app_name", "category": "コーディング", "is_regex": False, "priority": 10},
    {"pattern": "Atom", "match_target": "app_name", "category": "コーディング", "is_regex": False, "priority": 10},
    
    # 資料・設計
    {"pattern": "Notion", "match_target": "app_name", "category": "資料・設計", "is_regex": False, "priority": 10},
    {"pattern": "Figma", "match_target": "app_name", "category": "資料・設計", "is_regex": False, "priority": 10},
    {"pattern": "Photoshop", "match_target": "app_name", "category": "資料・設計", "is_regex": False, "priority": 10},
    {"pattern": "Illustrator", "match_target": "app_name", "category": "資料・設計", "is_regex": False, "priority": 10},
    {"pattern": "Word", "match_target": "app_name", "category": "資料・設計", "is_regex": False, "priority": 5},
    {"pattern": "Excel", "match_target": "app_name", "category": "資料・設計", "is_regex": False, "priority": 5},
    {"pattern": "PowerPoint", "match_target": "app_name", "category": "資料・設計", "is_regex": False, "priority": 5},
    
    # 調べ物(ブラウザ)
    {"pattern": "Chrome|Firefox|Safari|Edge|Brave", "match_target": "app_name", "category": "調べ物", "is_regex": True, "priority": 5},
    
    # 連絡
    {"pattern": "Discord|Slack|Teams|Zoom|Skype", "match_target": "app_name", "category": "連絡", "is_regex": True, "priority": 10},
    
    # 休憩
    {"pattern": "YouTube|Netflix|Spotify|Apple Music", "match_target": "app_name", "category": "休憩", "is_regex": True, "priority": 10},
    {"pattern": "Steam|Epic Games", "match_target": "app_name", "category": "休憩", "is_regex": True, "priority": 10},
]
