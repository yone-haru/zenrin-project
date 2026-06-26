import hashlib

from app.core.config import settings

VECTOR_DIM = 8


def generate_embedding(text: str) -> list[float]:
    """テキストをベクトル化する。

    Azure OpenAI（Embeddings）の認証情報が未設定の間は、テキストのハッシュ値から
    決定的な疑似ベクトルを生成するスタブとする。認証情報を設定後、実際のAPI呼び出しに差し替える。
    """
    if not settings.azure_openai_api_key:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [byte / 255 for byte in digest[:VECTOR_DIM]]

    raise NotImplementedError("Azure OpenAI（Embeddings）連携は未実装です")
