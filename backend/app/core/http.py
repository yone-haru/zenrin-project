"""共有 httpx.AsyncClient とリトライ付きリクエストヘルパー。

FastAPIのlifespanで起動時に1つだけAsyncClientを生成し、全外部API呼び出しで
使い回す（コネクションプール再利用のため）。5xx応答・接続エラー時は
指数バックオフで最大 `max_retries` 回まで再試行する。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

USER_AGENT = "school-route-safety-mvp/1.0"

_client: httpx.AsyncClient | None = None


def create_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=settings.http_timeout_s,
        headers={"User-Agent": USER_AGENT},
    )


async def startup_http_client() -> None:
    global _client
    _client = create_client()


async def shutdown_http_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def get_client() -> httpx.AsyncClient:
    """共有クライアントを返す。未起動（テスト等）の場合は都度生成する。"""
    if _client is None:
        return create_client()
    return _client


async def request_with_retry(
    method: str,
    url: str,
    *,
    max_retries: int | None = None,
    **kwargs: Any,
) -> httpx.Response:
    """5xx応答・接続エラー時に指数バックオフで再試行するHTTPリクエスト。

    4xx応答はリトライ対象外（クライアント側の問題のため即座に返す）。
    """
    retries = settings.http_max_retries if max_retries is None else max_retries
    client = get_client()
    owns_client = client is not _client

    try:
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                response = await client.request(method, url, **kwargs)
                if response.status_code >= 500 and attempt < retries:
                    logger.warning(
                        "外部API %s %s が %d を返却、再試行します (%d/%d)",
                        method,
                        url,
                        response.status_code,
                        attempt + 1,
                        retries,
                    )
                    await asyncio.sleep(2**attempt)
                    continue
                return response
            except httpx.TransportError as error:
                last_error = error
                if attempt < retries:
                    logger.warning(
                        "外部API %s %s への接続に失敗、再試行します (%d/%d): %s",
                        method,
                        url,
                        attempt + 1,
                        retries,
                        error,
                    )
                    await asyncio.sleep(2**attempt)
                    continue
                raise

        if last_error is not None:
            raise last_error
        raise RuntimeError("unreachable")
    finally:
        if owns_client:
            await client.aclose()
