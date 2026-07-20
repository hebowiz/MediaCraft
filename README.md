# MediaCraft

MediaCraftは、フレーム単位の映像確認にも対応するWindows向けデスクトップメディアプレイヤーです。

Phase 1～6と初期MVPは完了しています。設定画面、ファイルログ、未処理例外保護、
Windows向けone-folder配布基盤まで実装済みです。

## 開発環境

- Windows 10 / 11
- Python 3.11.9
- PySide6
- mpv / libmpv
- PyAV（CFR/VFR判定）
- Windows Media Player ActiveX（AMV4のDirectShow/VfW再生）

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

## 利用できる機能

- ファイル選択とドラッグ＆ドロップによる動画・音声ファイルの読み込み
- MP3、M4A、AAC、WAV、FLAC、Ogg Vorbis、Opus、WMA、AIFFの音声再生
- 音声ファイルのジャケット画像、タイトル、アーティスト、アルバム、ビットレート表示
- AMV4 AVIの自動検出と、Windowsにインストール済みのAMV4 VfWコーデックによる再生
- 再生、一時停止、停止
- シークバーと5秒／30秒単位のシーク
- 現在時刻と総時間の表示
- 音量変更とミュート
- 0.10x～4.00xの再生速度変更
- 動画領域のクリックによる再生／一時停止
- 基本的なフルスクリーン切り替え
- フルスクリーン時の半透明オーバーレイ操作UI
- 通常モードでの1フレーム送り／戻し（再生中は自動一時停止）
- フレーム確認モードでの1／10／100フレーム操作
- フレーム番号、FPS／VFR判定、ミリ秒単位の時刻表示
- 可変フレームレート動画の推定フレーム番号と`VFR`表示
- 右サイドパネルのプレイリスト表示・非表示
- 複数ファイル／フォルダ直下の動画・音声追加
- プレイリストへのドロップは追加入力、その他の領域へのドロップは新規リストとして置換
- プレイリストの削除、全消去、ドラッグ並び替え、ダブルクリック再生
- 前／次ファイル操作と、再生終了時の自動送り
- リスト末尾の終了時は先頭を選択して停止し、空リスト時は初期画面へ復帰
- シャッフル再生と、プレイリスト全体／1ファイルのリピート再生
- A点／B点の設定・解除・移動とA-Bリピート
- シークバー上のA/Bマーカーとリピート区間表示
- シークバーホバー位置のサムネイル・時刻・フレーム番号表示
- バックグラウンド生成とLRUキャッシュによるサムネイル再利用
- 動画全体の粗いサムネイル先読みと、ホバー位置の高解像度画像への差し替え
- PNG／JPEG形式の映像スクリーンショット保存
- スクリーンショット保存先と形式の設定保持
- 保存完了時のトースト通知
- フルスクリーン再生中の操作UI・マウスカーソル自動非表示
- バックグラウンド解析によるプレイリスト再生時間表示
- ウィンドウ位置、音量、ミュート、再生速度の保存
- 設定画面によるスクリーンショット・サムネイル先読み設定
- ローテーション付きファイルログと未処理例外の記録
- アプリ内の再生ボタンを基調にしたMediaCraftアイコン
- ヘルプメニューから参照できるモード別キーボードショートカット一覧

### 音声ファイルについて

音声ファイルでは、埋め込みジャケット画像を中央へ大きく表示し、その下にタイトル、
アーティスト、アルバム、ビットレートを表示します。ジャケット画像がない場合は画像領域を
空白のまま維持し、タイトルがない場合はファイル名を表示します。シーク、再生速度変更、
音量、A-Bリピート、プレイリスト操作は動画と同様に利用できます。
映像を持たないため、フレーム操作、FPS／Frame表示、シークバーのサムネイル、
スクリーンショットは無効になります。

正式な対応拡張子は`.mp3`、`.m4a`、`.aac`、`.wav`、`.flac`、`.ogg`、`.opus`、
`.wma`、`.aif`、`.aiff`です。DRM保護コンテンツには対応しません。
古いMP3で、CP932／Shift-JISの日本語タグがISO-8859-1として誤って記録されている
場合は、明確な文字化けパターンを検出できた項目だけ表示時に補正します。

### AMV4 AVIについて

AMV4を検出した場合は、アプリ本体をクラッシュさせる可能性があるPyAV解析を行わず、
AVIヘッダーから再生時間とフレームレートを安全に取得します。再生にはWindowsへ登録済みの
64bit版AMV4 VfWコーデックが必要です。AMV4コーデック本体はMediaCraftには同梱しません。

AMV4はWindows Media PlayerのDirectShow/VfW経路へ自動的に切り替えて再生します。
通常形式は従来どおりlibmpvを使用します。AMV4ではシークバー上のサムネイル表示は
利用できません。AMV4の再生速度変更はフレームクロック再生で実現するため、
1.00倍以外では音声を再生できません。

## 主な操作

以下のキーボードショートカットは、プレイリスト表示切り替えを除いてフルスクリーン表示中も利用できます。`Ctrl+L`は通常表示へ戻るまで無効になります。
アプリ内では「ヘルプ」→「キーボードショートカット...」から全操作を確認できます。

| 操作 | 動作 |
| --- | --- |
| `Ctrl+O` | 1件または複数のファイルを開き、新しいプレイリストを作成 |
| `Ctrl+S` | 現在の映像フレームを保存 |
| `Ctrl+L` | プレイリスト表示切り替え |
| `Space` / `Enter` | 再生／一時停止 |
| `S` | 停止して先頭へ戻る |
| `←` / `→` | 5秒戻し／送り |
| `Shift+←` / `Shift+→` | 30秒戻し／送り |
| `,` / `.` | 1フレーム戻し／送り |
| `I` | フレーム確認モード切り替え |
| `←` / `→`（フレーム確認モード） | 1フレーム戻し／送り（長押し対応） |
| `Shift+←` / `Shift+→`（同モード） | 10フレーム戻し／送り |
| `Ctrl+←` / `Ctrl+→`（同モード） | 100フレーム戻し／送り |
| `↑` / `↓` | 音量変更 |
| `M` | ミュート切り替え |
| `[` / `]` | 再生速度を0.05x変更 |
| `Backspace` | 再生速度を1.00xへ戻す |
| `F` / 動画領域をダブルクリック | フルスクリーン切り替え |
| `Esc` | フレーム確認モード解除、またはフルスクリーン解除 |
| `PageUp` / `PageDown` | 前／次のファイル |
| `A` / `B` | 現在位置をA点／B点に設定 |
| `R` | A-Bリピート切り替え |
| `Shift+A` / `Shift+B` | A点／B点を解除 |
| 動画領域でマウスホイール | 音量変更 |
| `Ctrl+マウスホイール` | 再生速度変更 |

## テスト

```powershell
python -m pytest
```

## Windows向けビルド

開発依存関係とlibmpvを準備した後、PowerShellで次を実行します。

```powershell
.\scripts\build_windows.ps1
```

アイコンのSVGを変更した場合は、ビルド前に次を実行してマルチサイズICOを再生成します。

```powershell
.venv\Scripts\python.exe scripts\generate_icon.py
```

Pythonを必要としないone-folder形式のアプリが
`dist\MediaCraft\MediaCraft.exe`へ生成されます。配布時は`MediaCraft`フォルダ全体を
コピーしてください。`libmpv-2.dll`とPySide6・PyAVの依存ファイルも同フォルダへ
収集されます。`LICENSE`、`THIRD_PARTY_NOTICES.md`、`LICENSES`フォルダも配布物へ
自動的に同梱されます。これらを削除せず、`MediaCraft`フォルダ全体を配布してください。

ローカルでのビルド、起動、通常終了は検証済みです。正式配布前には、Pythonや
開発ツールを導入していないクリーンなWindows環境での最終確認を行います。

実行ログはWindowsのローカルアプリデータ配下にある
`MediaCraft\logs\mediacraft.log`へ保存され、2 MiBごとに最大3世代まで保持されます。

## リリース

`main`へのpushとPull Requestでは、GitHub ActionsがPython 3.11.9環境で全テストを
実行します。`pyproject.toml`のバージョンと一致する`v*`タグをpushすると、Windows版の
テスト、libmpv取得、one-folderビルド、ZIP圧縮、SHA-256生成、GitHub Release作成まで
自動実行されます。リリース時の主要依存バージョンは`requirements-lock.txt`で固定されます。

```powershell
git tag v0.3.0
git push origin v0.3.0
```

プレリリースタグは`v0.3.0-rc.1`のように指定します。GitHubの「Actions」→
「Windows Release」→「Run workflow」から手動実行することもできます。既存Releaseに
対して再実行した場合は、ZIPとSHA-256ファイルを新しいビルドで置き換えます。

## ライセンス

MediaCraftはGNU General Public License version 3以降（GPL-3.0-or-later）で
提供します。第三者コンポーネント、各ライセンスおよび対応ソースの案内は
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)を参照してください。

依存関係や配布バイナリを更新した場合は、ライセンス内容を再確認したうえで次を実行し、
配布用ライセンス全文を更新してください。

```powershell
.venv\Scripts\python.exe scripts\collect_licenses.py
```
