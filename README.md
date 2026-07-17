# 通学路あんぜんマップ（通学路危険動線解析システム）

出発地・目的地を指定すると、複数の通学ルート候補を**安全スコア（0〜100点・A〜Eグレード）で採点して比較**し、ルート上の危険地点を地図に可視化するWebアプリ。危険判定は次の3つのデータソースを組み合わせて行う。

1. **OSM道路構造データ**（Overpass API）: 歩道の有無・幹線道路・信号や横断歩道のない交差点など
2. **警察庁交通事故オープンデータ**: 実際の事故発生地点（長崎県周辺、2022〜2023年、約15,000件を同梱）
3. **住民の写真通報**: 危険箇所の写真＋コメントを投稿でき、AI（Azure OpenAI・任意設定）が危険要因を記述・スコアリング

対象ユーザーは小学生の保護者・自治体職員。開発ルールは [CLAUDE.md](./CLAUDE.md)、詳細仕様は [要件定義書](./要件定義書_通学路危険動線解析システム.md) を参照。

## 主な機能

- **安全ルート比較**: OSRMの代替ルート（最大3本）をそれぞれ危険解析し、最も安全なルートを「推奨」として提示。カードで切替でき、地図上では非選択ルートも破線表示
- **安全スコア**: 危険地点の危険度（1〜5）と住民通報を距離あたりのペナルティに換算し、0〜100点・A〜Eグレードで採点（`backend/app/services/safety_score.py`）
- **危険地点の詳細**: 道路種別・歩道の有無・付近の事故件数・危険要因をモーダルで表示
- **住民の写真通報**: 地図クリック→写真＋コメント投稿。AIが説明文と危険度を自動付与
- **通報管理（自治体向け）**: URL に `?admin=1` を付けると管理パネルを表示。`ADMIN_TOKEN` で認証し、通報を「確認済み／却下」に更新
- **共有URL**: 検索条件がURLに同期され、リンクを開くだけで同じルートを再現。「共有」ボタンでコピー
- **現在地から検索**（Geolocation）／**印刷用レイアウト**（学校配布向け）／**PWA対応**（ホーム画面に追加可能）

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

## Google Maps Platform 統合（任意・推奨）

APIキーを設定すると、地図・徒歩ルート・地点検索が Google に切り替わる（**未設定時は自動的に OSM/OSRM/Nominatim 構成で動作**するので必須ではない）。

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクト作成 → 課金を有効化
2. **Maps JavaScript API / Routes API / Places API (New)** の3つを有効化
3. APIキーを作成（アプリケーション制限で HTTPリファラー `http://localhost:5173/*` 等を推奨）
4. キーを設定（`.env` はコミットされない）:
   - `backend/.env` → `GOOGLE_MAPS_API_KEY=<キー>`（Routes API・Places が有効になる）
   - `frontend/.env` → `VITE_GOOGLE_MAPS_API_KEY=<キー>`（地図表示が Google Maps になる）
5. （任意）Cloud Console の「マップ管理」で Map ID を作成し `frontend/.env` の `VITE_GOOGLE_MAPS_MAP_ID=` に設定すると独自スタイルの地図になる。未設定時はGoogle公式のデモID（`DEMO_MAP_ID`・開発用）で描画される

Google 経路は本物の徒歩ルート＋複数候補を返すため、OSRMデモサーバの「車ルートしか返さない」制約と Nominatim の日本語検索の弱さが同時に解消される。無料枠（各API 月1万コール程度）内なら課金は発生しない。

### 本番運用時の注意（外部API）

デフォルトでは無料の公開インスタンスを利用しているため、本格運用時は差し替えること。

| サービス | 用途 | デフォルト | 本番推奨 |
|---|---|---|---|
| OSRM | ルート検索 | 公開デモサーバ（**実質carルートのみ・商用不可**） | [自前ホスト](https://github.com/Project-OSRM/osrm-backend)（foot.luaプロファイル）。`OSRM_BASE_URL` で差し替え |
| Nominatim | ジオコーディング | 公開インスタンス（1req/秒制限。バックエンドでレート制御・キャッシュ済み） | 自前ホスト or 商用API。`NOMINATIM_URL` で差し替え |
| Overpass | 道路構造 | 公開インスタンス（1検索＝全ルート合成bboxで1クエリ＋1時間キャッシュ） | 自前ホスト。`OVERPASS_API_URL` で差し替え |
| 地図タイル | 表示 | CARTO Voyager（OSMベースの淡色タイル。要attribution・大規模利用はCARTO契約） | ゼンリン地図タイル（`frontend/.env` の `VITE_ZENRIN_MAP_API_KEY`、差し替えは MapView のタイルURL） |

## 事故データの更新

警察庁交通事故オープンデータ（https://www.npa.go.jp/publications/statistics/koutsuu/opendata/ ）の honhyo CSV をダウンロードし、前処理スクリプトで変換する。

```bash
cd backend
.venv/Scripts/python -m scripts.preprocess_accidents --help
```

同梱の `data/accidents.csv` は 2022〜2023年の実データを長崎県周辺（lat 32.4–34.8 / lng 128.3–130.5）で抽出したもの。

## 環境変数

- `backend/.env.example` … 外部APIのURL、Azure OpenAI（任意。未設定時は決定的スタブで動作）、CORS、アップロード上限、`ADMIN_TOKEN`（通報管理用。未設定時は管理APIが常に401）など
- `frontend/.env.example` … バックエンドAPIのベースURL（本番Dockerでは空＝同一オリジン）

## 通報管理（自治体職員向け）

1. `backend/.env` に `ADMIN_TOKEN=<推測されにくい文字列>` を設定して起動
2. アプリのURLに `?admin=1` を付けて開くと右上に「管理」ボタンが表示される
3. トークンを入力すると通報一覧（写真・AI説明・ステータス）が表示され、「確認済み」「却下」に更新できる

API: `PATCH /api/reports/{id}/status`（ヘッダ `X-Admin-Token`、ボディ `{"status": "confirmed"|"rejected"|"unconfirmed"}`）、`GET /api/reports?status=` でフィルタ。

## データ出典

- 事故データ: 警察庁「交通事故統計情報のオープンデータ」
- 地図・道路データ: © OpenStreetMap contributors
