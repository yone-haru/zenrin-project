# 通学路危険動線解析システム

> 出発地・目的地を指定すると通学ルート上の危険地点（OSM道路構造＋警察庁事故データ＋住民の写真通報）を地図に可視化するWebアプリ。小学生の保護者・自治体職員が使う。

## 技術スタック
- 言語: Python 3.10 互換必須（ローカルが3.10。`tomllib`・3.11+構文は使わない）/ TypeScript strict
- フレームワーク: FastAPI / React 19 + Vite + react-leaflet 5
- DB: SQLite（stdlib sqlite3、`backend/data/app.db`、WAL）。外部DBサーバなし
- テスト: pytest（外部APIは全てモック、オフラインで通ること）
- 外部API: OSRM（ルート）/ Nominatim（ジオコーディング）/ Overpass（道路構造）— いずれも無料公開インスタンス。Azure OpenAIは任意（未設定時は決定的スタブ）

## コマンド
```bash
# backend（backend/ で実行、venv: .venv）
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt   # install
.venv/Scripts/python -m uvicorn app.main:app --reload                            # dev
.venv/Scripts/python -m pytest                                                   # test

# frontend（frontend/ で実行）
npm install        # install
npm run dev        # dev（http://localhost:5173）
npm run build      # build（tsc -b && vite build ＝型チェック込み）
npm run lint       # lint
```

## プロジェクト構成
```
backend/app/
├── api/        # ルーター（route.py=ルート検索+危険解析, reports.py=写真通報）
├── services/   # 外部API・解析パイプライン（hazard_analysis が中核、safety_score=採点）
├── core/       # config / database / http（共有クライアント・リトライ）
└── scripts/    # preprocess_accidents.py（警察庁CSV→accidents.csv 変換）
frontend/src/
├── components/ # MapView / SearchPanel / RouteCards（ルート比較）/ HazardPanel / AdminPanel 等
├── hooks/      # useRoute / useGeocode（デバウンスサジェスト）
└── api/        # APIクライアント（契約v3は .claude/plan.md 参照。/api/route は routes配列を返す）
```

## ハマりどころ・既知の問題（随時追記・消さない）
- OSRM公開デモサーバは foot プロファイル指定でも実質車ルートを返す・商用利用不可。本番は自前ホスト（README参照）。`OSRM_BASE_URL` で差し替え可
- OSRMデモサーバの duration は車速のため、footプロファイル時はバックエンドが 80m/分 で徒歩時間を再計算して返す（routing_service.py）
- Nominatim は 1リクエスト/秒 制限。バックエンドでレート制御＋キャッシュ済みなので、フロントから直接叩かないこと
- Nominatim は日本語の部分一致に弱い（「伊良林小学校」は0件、「長崎市立伊良林小学校」「長崎駅」はヒット）。`NOMINATIM_COUNTRY_CODES=jp` で国外の誤ヒットは抑制済み。根本解決はゼンリンAPI差し替え時
- Overpass は1検索（全代替ルートの合成bbox）で1回だけクエリする設計。per-route/per-point クエリに戻すと即レート制限に当たる
- 通報管理APIは `ADMIN_TOKEN` 未設定だと常に401（意図した挙動）。管理パネルはURLに `?admin=1` を付けたときだけ表示
- hazard_analysis のクラスタ統合半径（120m）はサンプリング間隔（50m）より大きくすること。40mにすると隣接サンプルが統合されずピンだらけになる（実測22個/1.3km）
- 警察庁 honhyo CSV は CP932・緯度経度がDMS圧縮形式（緯度9桁 DDMMSSsss / 経度10桁 DDDMMSSsss）。十進度への変換は preprocess_accidents.py 経由でのみ行う
- Windows Git Bash の curl は `-d` の日本語をCP932で送るため、日本語入りJSONボディは400（There was an error parsing the body）になる。サーバは正常。APIの手動テストは Python urllib 等でUTF-8明示で行う
- eslint-plugin-react-hooks v7 の `set-state-in-effect` ルールは useEffect 本体での直接 setState を禁止する（early-return分岐でも）。setTimeout/Promiseコールバック内に移すこと
- グローバルCSSの `svg { width/height: ... }` は Leaflet の overlay pane（ルート描画SVG）まで縮めてポリラインが消える。`.leaflet-overlay-pane svg { width: revert; ... }` の除外を必ず残すこと（index.css）
- Google Maps の mapId は Cloud Console に実在するIDでないとベクター地図が何も描画されない（エラー表示もほぼ無し）。未設定時は公式デモID `DEMO_MAP_ID` にフォールバックする実装（GoogleMapView.tsx、`VITE_GOOGLE_MAPS_MAP_ID` で上書き可）
- 本番Dockerはフロントのnginxが `/api`・`/uploads` をバックエンドへプロキシする同一オリジン構成。`VITE_API_BASE_URL` は空文字でビルドする（`?? 'http://localhost:8000'` は空文字を素通しするのが意図した挙動）
- ローカル Python は 3.10.0。Dockerfile は 3.12 だがコードは 3.10 互換を維持すること
- CLAUDE.md・README等ルート直下ファイルをサブエージェントと並行編集しない（過去に git checkout で編集が巻き戻された事故あり。ルート直下は統合担当だけが触る）

## 検証ループ（最重要・消さない）
- **IMPORTANT: コードを変更したら必ず `.venv/Scripts/python -m pytest`（backend）を実行し、全部通るまでコミットしない。**
- frontend は `npm run build` と `npm run lint` も通すこと。エラーは握りつぶさず、根本原因を直す。
- コミットは論理的な区切りで分ける。大きなタスクも自律的にこなしてよい。
- 成功を主張する前に証拠を示す（テスト出力・実行コマンドと結果）。

## やってはいけないこと（境界・消さない）
- **YOU MUST NOT: `.env` や認証情報・APIキーをコミットしない。**
- スコープ外の大規模リファクタはしない。ただし根本原因の修正に必要な隣接コードは触ってよい。
- `backend/data/app.db`・`backend/uploads/`・`backend/data/raw/` はコミットしない（.gitignore 済み）
- 外部公開APIのモックなしテストを書かない（CIオフラインで落ちる）
- 危険地点のダミーデータをAPIレスポンスに混ぜない（過去に `_sample_hazards` で偽データを返していた反省。デモ用データは明示的なシード投入で行う）

## エージェントの動き方（ループエンジニアリング・消さない）
- **止まらない。途中で確認を求めない。** 仮定が必要なら合理的なベストを選び、何を仮定したか1行残して進む。
- ゴール未達・エラー発生いずれも止まらない。次の手を自分で決めて続行する（テスト修正・別アプローチ・追加調査など）。
- 数字・日付・仕様はファイルに根拠がない限り使わない。根拠がなければ「仮定:」と明記して進む。
- 複数ファイルにまたがる変更は、プランを先に `.claude/plan.md` へ書いてから実行する。
- ループ中に得た知見・進捗・試みたことは `.claude/loop-result.md` に随時記録する。
- **ループ中にプロジェクト固有の罠を発見したら、即座に「ハマりどころ」セクションに追記する。** 次のループが同じミスを繰り返さない。
- 実装と検証は分離する。実装後は別サブエージェント（Agent tool）に検証・レビューを依頼してよい。

### 停止条件（これ以外は止めない）
1. **完了**: backend pytest 全通過 + frontend build/lint 通過
2. **試行上限**: 15ターン超えても前進なし → 原因と試みたことを `.claude/loop-result.md` に書いて停止
