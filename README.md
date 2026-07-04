# 通学路危険動線解析システム

出発地・目的地を指定すると、通学ルート上の危険地点を地図に可視化するWebアプリ。危険判定は次の3つのデータソースを組み合わせて行う。

1. **OSM道路構造データ**（Overpass API）: 歩道の有無・幹線道路・信号や横断歩道のない交差点など
2. **警察庁交通事故オープンデータ**: 実際の事故発生地点（長崎県周辺、2022〜2023年、約15,000件を同梱）
3. **住民の写真通報**: 危険箇所の写真＋コメントを投稿でき、AI（Azure OpenAI・任意設定）が危険要因を記述・スコアリング

対象ユーザーは小学生の保護者・自治体職員。開発ルールは [CLAUDE.md](./CLAUDE.md)、詳細仕様は [要件定義書](./要件定義書_通学路危険動線解析システム.md) を参照。

## 構成

```
.
├── backend/    # FastAPI（ルート検索・危険解析パイプライン・通報API）
│   ├── app/services/hazard_analysis_service.py  # 解析の中核（サンプリング→スコアリング→クラスタ統合）
│   ├── scripts/preprocess_accidents.py          # 警察庁CSV → accidents.csv 変換
│   └── data/accidents.csv                       # 前処理済み事故データ（コミット対象）
└── frontend/   # React + TypeScript + Vite + Leaflet（地図UI・通報フォーム）
```

## 開発環境

### backend

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows (Git Bash)
pip install -r requirements.txt
cp .env.example .env            # APIキー等は任意（未設定でも動く）
uvicorn app.main:app --reload
```

`http://localhost:8000/health` で `{"status": "ok"}` が返れば起動成功。APIドキュメントは `http://localhost:8000/docs`。

### frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev     # http://localhost:5173
```

### テスト・検証

```bash
cd backend && .venv/Scripts/python -m pytest   # 全テスト（外部APIはモック・オフラインで通る）
cd frontend && npm run build && npm run lint   # 型チェック込みビルド + Lint
```

## 本番デプロイ（Docker）

```bash
cp backend/.env.example backend/.env   # 必要に応じて編集
docker compose up -d --build
```

- `http://localhost/`（ポート80）でフロントエンドが配信され、nginx が `/api`・`/uploads` をバックエンドへプロキシする（同一オリジンのためCORS設定不要）
- 投稿データ（SQLite）とアップロード画像は名前付きボリューム `backend-data` / `backend-uploads` に永続化される

### 本番運用時の注意（外部API）

デフォルトでは無料の公開インスタンスを利用しているため、本格運用時は差し替えること。

| サービス | 用途 | デフォルト | 本番推奨 |
|---|---|---|---|
| OSRM | ルート検索 | 公開デモサーバ（**実質carルートのみ・商用不可**） | [自前ホスト](https://github.com/Project-OSRM/osrm-backend)（foot.luaプロファイル）。`OSRM_BASE_URL` で差し替え |
| Nominatim | ジオコーディング | 公開インスタンス（1req/秒制限。バックエンドでレート制御・キャッシュ済み） | 自前ホスト or 商用API。`NOMINATIM_URL` で差し替え |
| Overpass | 道路構造 | 公開インスタンス（ルートごとに1クエリ＋1時間キャッシュ） | 自前ホスト。`OVERPASS_API_URL` で差し替え |
| 地図タイル | 表示 | OpenStreetMap | ゼンリン地図タイル（`frontend/.env` の `VITE_ZENRIN_MAP_API_KEY`、差し替えは MapView のタイルURL） |

## 事故データの更新

警察庁交通事故オープンデータ（https://www.npa.go.jp/publications/statistics/koutsuu/opendata/ ）の honhyo CSV をダウンロードし、前処理スクリプトで変換する。

```bash
cd backend
.venv/Scripts/python -m scripts.preprocess_accidents --help
```

同梱の `data/accidents.csv` は 2022〜2023年の実データを長崎県周辺（lat 32.4–34.8 / lng 128.3–130.5）で抽出したもの。

## 環境変数

- `backend/.env.example` … 外部APIのURL、Azure OpenAI（任意。未設定時は決定的スタブで動作）、CORS、アップロード上限など
- `frontend/.env.example` … バックエンドAPIのベースURL（本番Dockerでは空＝同一オリジン）

## データ出典

- 事故データ: 警察庁「交通事故統計情報のオープンデータ」
- 地図・道路データ: © OpenStreetMap contributors
