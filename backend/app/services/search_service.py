import json
import math
from pathlib import Path
from uuid import UUID

from app.core.config import settings

VECTOR_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
VECTOR_FILE = VECTOR_DATA_DIR / "vectors.json"


def _ensure_file() -> None:
    VECTOR_DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not VECTOR_FILE.exists():
        VECTOR_FILE.write_text("[]", encoding="utf-8")


def index_report(report_id: UUID, text: str, vector: list[float]) -> None:
    """テキスト記述とベクトルを検索用ストアに登録する。

    Azure AI Searchの認証情報が未設定の間は、ローカルJSONファイルに追記するスタブとする。
    認証情報を設定後、実際のAzure AI Search登録処理に差し替える。
    """
    if not settings.azure_search_api_key:
        _ensure_file()
        records = json.loads(VECTOR_FILE.read_text(encoding="utf-8"))
        records.append({"report_id": str(report_id), "text": text, "vector": vector})
        VECTOR_FILE.write_text(
            json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return

    raise NotImplementedError("Azure AI Search連携は未実装です")


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def find_similar_report_ids(report_id: UUID, limit: int = 5) -> list[tuple[UUID, float]]:
    """指定した投稿に近い危険パターンを持つ投稿を、ベクトル類似度の高い順に返す。"""
    _ensure_file()
    vectors = json.loads(VECTOR_FILE.read_text(encoding="utf-8"))

    target = next((v for v in vectors if v["report_id"] == str(report_id)), None)
    if target is None:
        return []

    scored = [
        (UUID(v["report_id"]), _cosine_similarity(target["vector"], v["vector"]))
        for v in vectors
        if v["report_id"] != str(report_id)
    ]
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:limit]
