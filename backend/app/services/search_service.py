import json
import math
import threading
from uuid import UUID

from app.core.database import get_connection

_write_lock = threading.Lock()


def index_report(report_id: UUID, text: str, vector: list[float]) -> None:
    """テキスト記述とベクトルをローカルSQLiteの検索用ストアに登録する。"""
    conn = get_connection()
    with _write_lock:
        conn.execute(
            """
            INSERT INTO vectors (report_id, text, vector)
            VALUES (?, ?, ?)
            ON CONFLICT(report_id) DO UPDATE SET text=excluded.text, vector=excluded.vector
            """,
            (str(report_id), text, json.dumps(vector)),
        )
        conn.commit()


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def find_similar_report_ids(report_id: UUID, limit: int = 5) -> list[tuple[UUID, float]]:
    """指定した投稿に近い危険パターンを持つ投稿を、ベクトル類似度の高い順に返す。"""
    conn = get_connection()
    rows = conn.execute("SELECT report_id, vector FROM vectors").fetchall()

    vectors = {row["report_id"]: json.loads(row["vector"]) for row in rows}
    target = vectors.get(str(report_id))
    if target is None:
        return []

    scored = [
        (UUID(rid), _cosine_similarity(target, vec))
        for rid, vec in vectors.items()
        if rid != str(report_id)
    ]
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:limit]
