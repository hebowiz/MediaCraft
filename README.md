# MediaCraft

MediaCraftは、フレーム単位の映像確認にも対応するWindows向けデスクトップ動画プレイヤーです。

現在は初期構成の準備段階です。機能は仕様書のPhase 1から順番に実装します。

## 開発環境

- Windows 10 / 11
- Python 3.11.9
- PySide6
- mpv / libmpv

仕様の詳細は[`docs/video_player_spec.md`](docs/video_player_spec.md)を参照してください。

## 仮想環境

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```
