# Docker セットアップガイド

このプロジェクトをDockerで起動するための手順です。チームメンバーは各自のPCにDocker Desktopを入れるだけで、Python/Node.jsのバージョン差異を気にせず同じ環境で開発できます。

## 前提条件

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) をインストールしておくこと（Windows / Mac 共通）
- Docker Desktop起動時に「WSL2 based engine」が有効になっていること（Windowsの場合）

インストール確認:

```bash
docker --version
docker compose version
```

## 初回セットアップ

### 1. リポジトリをクローン

```bash
git clone <リポジトリURL>
cd ゼンリン
```

### 2. 環境変数ファイルを作成

`.env` はGit管理外なので、各自で `.env.example` をコピーして作成します。

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

APIキー未設定でも、モック/スタブで動く部分はそのまま起動できます（`CLAUDE.md` 参照）。実際のAzure OpenAI等のキーを持っている人は各ファイルに記入してください。

### 3. コンテナをビルドして起動

```bash
docker compose up --build
```

初回はビルドに数分かかります。以降は `--build` を付けなくてもキャッシュが効きます。

### 4. 動作確認

| サービス | URL |
|---|---|
| フロントエンド（React + Vite） | http://localhost:5173 |
| バックエンド（FastAPI） | http://localhost:8000 |
| バックエンドAPIドキュメント（Swagger） | http://localhost:8000/docs |
| ヘルスチェック | http://localhost:8000/health |

## 日常の使い方

### 起動・停止

```bash
# 起動（フォアグラウンド、ログがそのまま流れる）
docker compose up

# 起動（バックグラウンド）
docker compose up -d

# 停止
docker compose down
```

### ログを見る（バックグラウンド起動時）

```bash
docker compose logs -f
docker compose logs -f backend
docker compose logs -f frontend
```

### コードの変更は自動反映される

`backend/` と `frontend/` はホスト側のフォルダをコンテナにマウントしているため、ローカルでコードを編集すればコンテナ内のサーバーが自動でリロードされます（バックエンドは `uvicorn --reload`、フロントエンドは Vite の HMR）。コンテナの再起動は不要です。

### 依存パッケージを追加したとき

`requirements.txt` や `package.json` を変更した人は、他のメンバーに「再ビルドしてね」と伝えてください。

```bash
docker compose build
docker compose up
```

### コンテナの中に入って作業したいとき

```bash
docker compose exec backend bash
docker compose exec frontend sh
```

### 全部きれいにして作り直したいとき

```bash
docker compose down -v
docker compose up --build
```

`-v` を付けると `frontend-node-modules` の名前付きボリュームも削除され、`node_modules` がクリーンな状態から再インストールされます。

## 構成の補足

- バックエンドは画像アップロード(`backend/uploads/`)とJSONデータ(`backend/data/`)をローカルのファイルシステムに保存します。これらはホスト側にバインドマウントされているため、コンテナを再作成してもデータは消えません（Git管理外、`.gitignore`済み）。
- フロントエンドの `node_modules` はOS依存のネイティブバイナリを含むため、ホストの `node_modules` をそのまま使わず、コンテナ専用の名前付きボリューム（`frontend-node-modules`）に分離しています。ローカルで `npm install` した結果とコンテナ内の中身が違うのは仕様です。
- Vite開発サーバーはコンテナ内で動かすため `vite.config.ts` に `server.host: true` と `watch.usePolling: true` を設定しています（Dockerのバインドマウントではファイル変更イベントが届かない環境があるため、ポーリング方式に変更しています）。

## トラブルシューティング

- **ポートが衝突する**: ローカルで `uvicorn` や `npm run dev` を直接起動していると `8000` / `5173` が競合します。先に停止してください。
- **フロントエンドの変更が反映されない**: `docker compose down -v` → `docker compose up --build` で `node_modules` ボリュームを作り直してください。
- **`.env` の変更が反映されない**: `.env` は起動時に読み込まれるため、変更後はコンテナの再起動（`docker compose restart backend` など）が必要です。
