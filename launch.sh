#!/bin/bash

# 文字コードをUTF-8に設定
export LANG=ja_JP.UTF-8

echo "===================================="
echo "集中時間トラッカー 起動中..."
echo "===================================="
echo ""

# スクリプトのディレクトリに移動
cd "$(dirname "$0")"

# Pythonの確認
if ! command -v python3 &> /dev/null; then
    echo "[エラー] Python 3がインストールされていません"
    echo "https://www.python.org/downloads/ からインストールしてください"
    read -p "Enterキーを押して終了..."
    exit 1
fi

echo "Python バージョン: $(python3 --version)"

# 仮想環境の確認と作成
if [ ! -d ".venv" ]; then
    echo "仮想環境を作成中..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "[エラー] 仮想環境の作成に失敗しました"
        read -p "Enterキーを押して終了..."
        exit 1
    fi
fi

# 仮想環境のアクティベート
echo "仮想環境をアクティベート中..."
source .venv/bin/activate
if [ $? -ne 0 ]; then
    echo "[エラー] 仮想環境のアクティベートに失敗しました"
    read -p "Enterキーを押して終了..."
    exit 1
fi

# 依存関係のインストール
echo "依存関係を確認中..."
pip install -q -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[警告] 一部のパッケージのインストールに失敗しました"
    echo "アプリは起動しますが、一部機能が制限される可能性があります"
fi

echo ""
echo "===================================="
echo "アプリケーションを起動します"
echo "===================================="
echo ""

# アプリケーション起動
python3 -m src.main

# 終了時
echo ""
echo "アプリケーションが終了しました"
read -p "Enterキーを押して終了..."
