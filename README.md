# MediaCraft

MediaCraftは、フレーム単位の映像確認にも対応するWindows向けデスクトップ動画プレイヤーです。

現在はPhase 1の基本再生機能を実装しています。

## 開発環境

- Windows 10 / 11
- Python 3.11.9
- PySide6
- mpv / libmpv

仕様の詳細は[`docs/video_player_spec.md`](docs/video_player_spec.md)を参照してください。

## セットアップ

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts\setup_mpv.py
```

`setup_mpv.py`は、[mpv公式サイトのWindows向け案内](https://mpv.io/installation/)に掲載されているshinchiro版から、64bit版libmpvを`vendor/mpv`へ配置します。取得したバイナリはGit管理対象外です。

## 起動

セットアップ完了後、リポジトリ直下の`MediaCraft.bat`をダブルクリックすると起動できます。

コマンドラインから起動する場合は、仮想環境を有効にして次のいずれかを実行します。

```powershell
python -m mediacraft
```

```powershell
mediacraft
```

## Phase 1で利用できる機能

- ファイル選択とドラッグ＆ドロップによる単一動画の読み込み
- 再生、一時停止、停止
- シークバーと5秒／30秒単位のシーク
- 現在時刻と総時間の表示
- 音量変更とミュート
- 0.10x～4.00xの再生速度変更
- 動画領域のクリックによる再生／一時停止
- 基本的なフルスクリーン切り替え
- ウィンドウ位置、音量、ミュート、再生速度の保存

複数ファイルをドロップした場合、Phase 1では先頭のファイルだけを開きます。

## 主な操作

| 操作 | 動作 |
| --- | --- |
| `Ctrl+O` | ファイルを開く |
| `Space` / `Enter` | 再生／一時停止 |
| `S` | 停止して先頭へ戻る |
| `←` / `→` | 5秒戻し／送り |
| `Shift+←` / `Shift+→` | 30秒戻し／送り |
| `↑` / `↓` | 音量変更 |
| `M` | ミュート切り替え |
| `[` / `]` | 再生速度を0.05x変更 |
| `Backspace` | 再生速度を1.00xへ戻す |
| `F` / 動画領域をダブルクリック | フルスクリーン切り替え |
| `Esc` | フルスクリーン解除 |
| 動画領域でマウスホイール | 音量変更 |
| `Ctrl+マウスホイール` | 再生速度変更 |

## テスト

```powershell
python -m pytest
```
