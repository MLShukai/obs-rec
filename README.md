# obs-rec

OBSを使った自動録画・Discord投稿ボット

## 概要

`obs-rec`は、OBS Studioの画面録画を定期的に実行し、録画した動画をDiscordチャンネルに自動投稿するPython製のボットです。

## 主な機能

- OBS WebSocketを通じた録画制御
- 指定間隔での自動録画
- 動画の自動圧縮（Discord制限対応）
- MP4形式への自動変換

## 必要要件

- Python 3.12以降
- OBS Studio（WebSocketサーバー有効化済み）
- ffmpeg（動画圧縮用）
- Discord Bot Token

## セットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/mlshukai/obs-rec.git
cd obs-rec
```

### 2. OBSの設定

1. OBS Studioを起動
2. `ツール` → `WebSocketサーバー設定` を開く
3. `WebSocketサーバーを有効にする` にチェック
4. ポート番号（デフォルト: 4455）を確認
5. 必要に応じてパスワードを設定

### 4. Discord Botの作成

1. [Discord Developer Portal](https://discord.com/developers/applications)にアクセス
2. 新しいアプリケーションを作成
3. `Bot`セクションでBotを作成しTokenをコピー
4. Botを対象のサーバーに招待（`Send Messages`と`Attach Files`権限が必要）

## 使い方

### Botの起動

```bash
./run.sh
```

### 動作確認

1. OBS Studioが起動していることを確認
2. Botが指定したDiscordチャンネルにアクセスできることを確認
3. 設定した間隔で録画が開始され、動画が投稿されることを確認

## 開発

### 開発環境のセットアップ

```bash
# 開発用依存関係を含めてインストール
uv sync --all-extras

# pre-commitフックのセットアップ
uv run pre-commit install
```

### コード品質チェック

```bash
# フォーマットとリント
make format

# 型チェック
make type

# テスト実行
make test

# すべてのチェックを実行
make run
```

### テストの実行

```bash
# 全テスト実行
uv run pytest

# カバレッジ付き
uv run pytest --cov=obs_rec

# 特定のテストファイルのみ
uv run pytest tests/test_bot.py
```

### プロジェクト構造

```
obs-rec/
├── src/obs_rec/
│   ├── __init__.py
│   ├── __main__.py      # エントリーポイント
│   ├── bot.py           # Discord Botメイン
│   ├── config.py        # 設定管理
│   ├── obs_client.py    # OBS制御
│   └── video_compressor.py  # 動画圧縮
├── tests/               # テストコード
├── .env.example         # 環境変数サンプル
├── pyproject.toml       # プロジェクト設定
└── uv.lock             # 依存関係ロック
```

## トラブルシューティング

### OBSに接続できない

- OBS Studioが起動しているか確認
- WebSocketサーバーが有効になっているか確認
- ホスト、ポート、パスワードが正しいか確認

### 動画が投稿されない

- Discord Botのトークンが正しいか確認
- チャンネルIDが正しいか確認
- Botに必要な権限があるか確認

### 動画サイズが大きすぎる

- `VIDEO_MAX_SIZE_MB`の値を調整（Discordの制限は通常10MB）
- ffmpegがインストールされているか確認

## ライセンス

MIT License - 詳細は[LICENSE](LICENSE)ファイルを参照
