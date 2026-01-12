@echo off
chcp 65001 > nul
echo ====================================
echo 集中時間トラッカー 起動中...
echo ====================================
echo.

cd /d "%~dp0"

REM Pythonの確認
python --version > nul 2>&1
if errorlevel 1 (
    echo [エラー] Pythonがインストールされていません
    echo https://www.python.org/downloads/ からインストールしてください
    pause
    exit /b 1
)

REM 仮想環境の確認と作成
if not exist ".venv" (
    echo 仮想環境を作成中...
    python -m venv .venv
    if errorlevel 1 (
        echo [エラー] 仮想環境の作成に失敗しました
        pause
        exit /b 1
    )
)

REM 仮想環境のアクティベート
echo 仮想環境をアクティベート中...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [エラー] 仮想環境のアクティベートに失敗しました
    pause
    exit /b 1
)

REM 依存関係のインストール
echo 依存関係を確認中...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo [警告] 一部のパッケージのインストールに失敗しました
    echo アプリは起動しますが、一部機能が制限される可能性があります
)

echo.
echo ====================================
echo アプリケーションを起動します
echo ====================================
echo.

REM アプリケーション起動
python -m src.main

REM 終了時
echo.
echo アプリケーションが終了しました
pause
