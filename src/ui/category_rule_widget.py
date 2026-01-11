"""
カテゴリ・ルール設定ウィンドウ
"""
from typing import Dict, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel,
    QDialog, QLineEdit, QComboBox, QCheckBox, QSpinBox,
    QColorDialog, QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from ..data.database import Database


class CategoryRuleWidget(QWidget):
    """カテゴリ・ルール設定ウィジェット"""
    
    data_changed = Signal()  # データ変更時のシグナル
    
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self._setup_ui()
        self._load_data()
    
    def _setup_ui(self) -> None:
        """UIをセットアップ"""
        layout = QVBoxLayout(self)
        
        # タブウィジェット
        tabs = QTabWidget()
        
        # カテゴリタブ
        category_widget = QWidget()
        category_layout = QVBoxLayout(category_widget)
        
        # カテゴリテーブル
        self.category_table = QTableWidget()
        self.category_table.setColumnCount(4)
        self.category_table.setHorizontalHeaderLabels(["カテゴリ名", "色", "生産的", "操作"])
        self.category_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        category_layout.addWidget(self.category_table)
        
        # カテゴリ追加ボタン
        add_category_btn = QPushButton("➕ カテゴリを追加")
        add_category_btn.clicked.connect(self._add_category)
        category_layout.addWidget(add_category_btn)
        
        tabs.addTab(category_widget, "カテゴリ")
        
        # ルールタブ
        rule_widget = QWidget()
        rule_layout = QVBoxLayout(rule_widget)
        
        # ルールテーブル
        self.rule_table = QTableWidget()
        self.rule_table.setColumnCount(6)
        self.rule_table.setHorizontalHeaderLabels(["パターン", "対象", "カテゴリ", "正規表現", "優先度", "操作"])
        self.rule_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        rule_layout.addWidget(self.rule_table)
        
        # ルール追加ボタン
        add_rule_btn = QPushButton("➕ ルールを追加")
        add_rule_btn.clicked.connect(self._add_rule)
        rule_layout.addWidget(add_rule_btn)
        
        tabs.addTab(rule_widget, "分類ルール")
        
        layout.addWidget(tabs)
    
    def _load_data(self) -> None:
        """データを読み込み"""
        self._load_categories()
        self._load_rules()
    
    def _load_categories(self) -> None:
        """カテゴリを読み込み"""
        categories = self.db.get_all_categories()
        self.category_table.setRowCount(len(categories))
        
        for row, cat in enumerate(categories):
            # カテゴリ名
            name_item = QTableWidgetItem(cat["name"])
            self.category_table.setItem(row, 0, name_item)
            
            # 色
            color_item = QTableWidgetItem(cat["color"])
            color_item.setBackground(QColor(cat["color"]))
            # 背景色に応じて文字色を調整
            color = QColor(cat["color"])
            if color.lightness() < 128:
                color_item.setForeground(QColor("#FFFFFF"))
            else:
                color_item.setForeground(QColor("#000000"))
            self.category_table.setItem(row, 1, color_item)
            
            # 生産的
            productive_item = QTableWidgetItem("✓" if cat["is_productive"] else "")
            productive_item.setTextAlignment(Qt.AlignCenter)
            self.category_table.setItem(row, 2, productive_item)
            
            # 操作ボタン
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            
            edit_btn = QPushButton("編集")
            edit_btn.clicked.connect(lambda checked, c=cat: self._edit_category(c))
            btn_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("削除")
            delete_btn.clicked.connect(lambda checked, c=cat: self._delete_category(c))
            btn_layout.addWidget(delete_btn)
            
            self.category_table.setCellWidget(row, 3, btn_widget)
    
    def _load_rules(self) -> None:
        """ルールを読み込み"""
        rules = self.db.get_all_rules()
        categories = {cat["id"]: cat for cat in self.db.get_all_categories()}
        
        self.rule_table.setRowCount(len(rules))
        
        for row, rule in enumerate(rules):
            # パターン
            pattern_item = QTableWidgetItem(rule["pattern"])
            self.rule_table.setItem(row, 0, pattern_item)
            
            # 対象
            target_map = {"app_name": "アプリ名", "process": "プロセス名", "title": "ウィンドウタイトル"}
            target_item = QTableWidgetItem(target_map.get(rule["match_target"], rule["match_target"]))
            self.rule_table.setItem(row, 1, target_item)
            
            # カテゴリ
            cat = categories.get(rule["category_id"], {"name": "不明"})
            category_item = QTableWidgetItem(cat["name"])
            self.rule_table.setItem(row, 2, category_item)
            
            # 正規表現
            regex_item = QTableWidgetItem("✓" if rule["is_regex"] else "")
            regex_item.setTextAlignment(Qt.AlignCenter)
            self.rule_table.setItem(row, 3, regex_item)
            
            # 優先度
            priority_item = QTableWidgetItem(str(rule["priority"]))
            priority_item.setTextAlignment(Qt.AlignCenter)
            self.rule_table.setItem(row, 4, priority_item)
            
            # 操作ボタン
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            
            edit_btn = QPushButton("編集")
            edit_btn.clicked.connect(lambda checked, r=rule: self._edit_rule(r))
            btn_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("削除")
            delete_btn.clicked.connect(lambda checked, r=rule: self._delete_rule(r))
            btn_layout.addWidget(delete_btn)
            
            self.rule_table.setCellWidget(row, 5, btn_widget)
    
    def _add_category(self) -> None:
        """カテゴリを追加"""
        dialog = CategoryDialog(self.db, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self._load_categories()
            self.data_changed.emit()
    
    def _edit_category(self, category: Dict) -> None:
        """カテゴリを編集"""
        dialog = CategoryDialog(self.db, category, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self._load_categories()
            self.data_changed.emit()
    
    def _delete_category(self, category: Dict) -> None:
        """カテゴリを削除"""
        reply = QMessageBox.question(
            self, "確認",
            f"カテゴリ「{category['name']}」を削除しますか？\n関連するルールも削除されます。",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.delete_category(category["id"])
            self._load_categories()
            self._load_rules()
            self.data_changed.emit()
    
    def _add_rule(self) -> None:
        """ルールを追加"""
        dialog = RuleDialog(self.db, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self._load_rules()
            self.data_changed.emit()
    
    def _edit_rule(self, rule: Dict) -> None:
        """ルールを編集"""
        dialog = RuleDialog(self.db, rule, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self._load_rules()
            self.data_changed.emit()
    
    def _delete_rule(self, rule: Dict) -> None:
        """ルールを削除"""
        reply = QMessageBox.question(
            self, "確認",
            f"ルール「{rule['pattern']}」を削除しますか？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.delete_rule(rule["id"])
            self._load_rules()
            self.data_changed.emit()


class CategoryDialog(QDialog):
    """カテゴリ追加・編集ダイアログ"""
    
    def __init__(self, db: Database, category: Dict = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.category = category
        self.is_edit = category is not None
        
        self.setWindowTitle("カテゴリを編集" if self.is_edit else "カテゴリを追加")
        self.setMinimumWidth(400)
        
        self._setup_ui()
        
        if self.is_edit:
            self._load_category_data()
    
    def _setup_ui(self) -> None:
        """UIをセットアップ"""
        layout = QVBoxLayout(self)
        
        # カテゴリ名
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("カテゴリ名:"))
        self.name_input = QLineEdit()
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # 色
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("色:"))
        self.color_input = QLineEdit("#B2BEC3")
        color_layout.addWidget(self.color_input)
        self.color_btn = QPushButton("色を選択")
        self.color_btn.clicked.connect(self._choose_color)
        color_layout.addWidget(self.color_btn)
        layout.addLayout(color_layout)
        
        # 生産的
        self.productive_check = QCheckBox("生産的なカテゴリ")
        self.productive_check.setChecked(True)
        layout.addWidget(self.productive_check)
        
        # ボタン
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("キャンセル")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
    
    def _load_category_data(self) -> None:
        """カテゴリデータを読み込み"""
        self.name_input.setText(self.category["name"])
        self.color_input.setText(self.category["color"])
        self.productive_check.setChecked(bool(self.category["is_productive"]))
    
    def _choose_color(self) -> None:
        """色を選択"""
        color = QColorDialog.getColor(QColor(self.color_input.text()), self)
        if color.isValid():
            self.color_input.setText(color.name())
    
    def _save(self) -> None:
        """保存"""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "エラー", "カテゴリ名を入力してください")
            return
        
        color = self.color_input.text().strip()
        is_productive = self.productive_check.isChecked()
        
        try:
            if self.is_edit:
                self.db.update_category(self.category["id"], name, color, is_productive)
            else:
                self.db.add_category(name, color, is_productive)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"保存に失敗しました: {e}")


class RuleDialog(QDialog):
    """ルール追加・編集ダイアログ"""
    
    def __init__(self, db: Database, rule: Dict = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.rule = rule
        self.is_edit = rule is not None
        
        self.setWindowTitle("ルールを編集" if self.is_edit else "ルールを追加")
        self.setMinimumWidth(500)
        
        self._setup_ui()
        
        if self.is_edit:
            self._load_rule_data()
    
    def _setup_ui(self) -> None:
        """UIをセットアップ"""
        layout = QVBoxLayout(self)
        
        # パターン
        pattern_layout = QHBoxLayout()
        pattern_layout.addWidget(QLabel("パターン:"))
        self.pattern_input = QLineEdit()
        self.pattern_input.setPlaceholderText("例: Chrome, Maya, Visual Studio")
        pattern_layout.addWidget(self.pattern_input)
        layout.addLayout(pattern_layout)
        
        # 対象
        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel("マッチ対象:"))
        self.target_combo = QComboBox()
        self.target_combo.addItems(["アプリ名", "プロセス名", "ウィンドウタイトル"])
        target_layout.addWidget(self.target_combo)
        layout.addLayout(target_layout)
        
        # カテゴリ
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("カテゴリ:"))
        self.category_combo = QComboBox()
        categories = self.db.get_all_categories()
        for cat in categories:
            self.category_combo.addItem(cat["name"], cat["id"])
        category_layout.addWidget(self.category_combo)
        layout.addLayout(category_layout)
        
        # 正規表現
        self.regex_check = QCheckBox("正規表現を使用")
        layout.addWidget(self.regex_check)
        
        # 優先度
        priority_layout = QHBoxLayout()
        priority_layout.addWidget(QLabel("優先度:"))
        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(0, 100)
        self.priority_spin.setValue(10)
        priority_layout.addWidget(self.priority_spin)
        priority_layout.addWidget(QLabel("(数値が大きいほど優先)"))
        priority_layout.addStretch()
        layout.addLayout(priority_layout)
        
        # ヘルプテキスト
        help_text = QLabel(
            "💡 ヒント:\n"
            "・パターンは部分一致で判定されます\n"
            "・正規表現を使うと複数パターンを1つのルールで設定できます\n"
            "　例: Chrome|Firefox|Safari → ブラウザ全般"
        )
        help_text.setStyleSheet("color: palette(mid); font-size: 11px; padding: 10px;")
        layout.addWidget(help_text)
        
        # ボタン
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("キャンセル")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
    
    def _load_rule_data(self) -> None:
        """ルールデータを読み込み"""
        self.pattern_input.setText(self.rule["pattern"])
        
        target_map = {"app_name": 0, "process": 1, "title": 2}
        self.target_combo.setCurrentIndex(target_map.get(self.rule["match_target"], 0))
        
        # カテゴリを選択
        for i in range(self.category_combo.count()):
            if self.category_combo.itemData(i) == self.rule["category_id"]:
                self.category_combo.setCurrentIndex(i)
                break
        
        self.regex_check.setChecked(bool(self.rule["is_regex"]))
        self.priority_spin.setValue(self.rule["priority"])
    
    def _save(self) -> None:
        """保存"""
        pattern = self.pattern_input.text().strip()
        if not pattern:
            QMessageBox.warning(self, "エラー", "パターンを入力してください")
            return
        
        target_map = {0: "app_name", 1: "process", 2: "title"}
        match_target = target_map[self.target_combo.currentIndex()]
        category_id = self.category_combo.currentData()
        is_regex = self.regex_check.isChecked()
        priority = self.priority_spin.value()
        
        try:
            if self.is_edit:
                self.db.update_rule(self.rule["id"], match_target, pattern, category_id, is_regex, priority)
            else:
                self.db.add_rule(match_target, pattern, category_id, is_regex, priority)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"保存に失敗しました: {e}")
