"""テキストをベクトル化する埋め込みサービス。

Azure OpenAI（text-embedding-3-small等）の認証情報が設定されていれば実際にREST APIを
呼び出す。未設定時はテキストのハッシュ値から決定的な疑似ベクトルを生成するスタブとして
動作する。実APIのレスポンス次元は可変（text-embedding-3-smallなら1536次元等）のため、
スタブも同じ次元数に固定しない（呼び出し側はコサイン類似度計算時に同じ生成元同士でのみ
比較する前提）。
"""

from __future__ import annotations

import hashlib
import logging

import httpx

from app.core.config import settings
from app.core.http import request_with_retry

logger = logging.getLogger(__name__)

STUB_VECTOR_DIM = 8


def _is_configured() -> bool:
    return bool(
        settings.azure_openai_api_key
        and settings.azure_openai_endpoint
        and settings.azure_openai_embedding_deployment
    )


def _stub_embedding(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [byte / 255 for byte in digest[:STUB_VECTOR_DIM]]


async def generate_embedding_async(text: str) -> list[float]:
    if not _is_configured():
        return _stub_embedding(text)

    url = (
        f"{settings.azure_openai_endpoint.rstrip('/')}/openai/deployments/"
        f"{settings.azure_openai_embedding_deployment}/embeddings"
        f"?api-version={settings.azure_openai_api_version}"
    )

    try:
        response = await request_with_retry(
            "POST",
            url,
            headers={"api-key": settings.azure_openai_api_key},
            json={"input": text},
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]
    except (httpx.HTTPError, KeyError, IndexError) as error:
        logger.warning("Azure OpenAI Embeddings呼び出しに失敗したためスタブベクトルを返します: %s", error)
        return _stub_embedding(text)


def generate_embedding(text: str) -> list[float]:
    """同期コンテキスト向け互換関数。未設定時のみ安全に同期利用できる。"""
    if not _is_configured():
        return _stub_embedding(text)

    import asyncio

    return asyncio.run(generate_embedding_async(text))
