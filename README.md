# 通学路危険動線解析システム

ゼンリン地図データ × 画像のAIベクトル分析で、通学路に潜む潜在的危険地点を可視化するWebシステム。

詳細な要件は [要件定義書_通学路危険動線解析システム.md](./要件定義書_通学路危険動線解析システム.md) を参照。
開発ルールは [CLAUDE.md](./CLAUDE.md) を参照。

## ディレクトリ構成

```
.
├── backend/   # FastAPI（API・AIパイプライン）
└── frontend/  # React + Vite + Leaflet（地図UI・通報フォーム）
```

## 開発環境の立ち上げ手順

### backend

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows (Git Bash)
# .venv\Scripts\Activate.ps1    # Windows (PowerShell)
pip install -r requirements.txt
cp .env.example .env            # 必要に応じてAPIキー等を設定
uvicorn app.main:app --reload
```

起動後、`http://localhost:8000/health` で `{"status": "ok"}` が返ることを確認する。

### frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

起動後、表示されたURL（既定 `http://localhost:5173`）をブラウザで開く。

## 環境変数

- `backend/.env.example`：Azure OpenAI（GPT-4o Vision / Embeddings）、Azure AI SearchのAPIキー等
- `frontend/.env.example`：バックエンドAPIのベースURL、ゼンリン地図APIキー等

APIキーが未設定の開発初期段階では、各機能はモック/スタブで動作する想定（詳細はCLAUDE.md参照）。
