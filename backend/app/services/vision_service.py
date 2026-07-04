"""画像から通学路の危険要因を記述するVision連携サービス。

Azure OpenAI（GPT-4o Vision）の認証情報が設定されていれば実際にREST APIを呼び出す。
未設定の場合は、画像パスのハッシュ値から固定候補を決定的に選ぶスタブとして動作する
（`random` は使わない＝同じ画像なら常に同じ結果になり、テストが再現可能になる）。
"""

from __future__ import annotations

import base64
import hashlib
import logging
from pathlib import Path

import httpx

from app.core.config import settings
from app.core.http import request_with_retry

logger = logging.getLogger(__name__)

_STUB_DESCRIPTIONS = [
    "ガードレールがなく、車道との境界が不明確である。",
    "見通しの悪いカーブがあり、対向車や人の存在に気づきにくい。",
    "街灯が少なく、夜間は視認性が低い。",
    "歩道が狭く、児童が車道側に寄って歩く必要がある。",
    "交差点の見通しが悪く、出会い頭の危険がある。",
]

_VISION_PROMPT = (
    "この画像は通学路の写真です。児童・生徒にとっての危険要因を、"
    "日本語で1〜2文の簡潔な説明にまとめてください。危険要因が見当たらない場合は"
    "その旨を簡潔に述べてください。"
)

_CONTENT_TYPE_BY_SUFFIX = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def _is_configured() -> bool:
    return bool(
        settings.azure_openai_api_key
        and settings.azure_openai_endpoint
        and settings.azure_openai_vision_deployment
    )


def _stub_description(image_path: Path) -> str:
    digest = hashlib.sha256(str(image_path).encode("utf-8")).digest()
    index = digest[0] % len(_STUB_DESCRIPTIONS)
    return _STUB_DESCRIPTIONS[index]


async def analyze_image_async(image_path: Path) -> str:
    if not _is_configured():
        return _stub_description(image_path)

    try:
        image_bytes = image_path.read_bytes()
    except OSError as error:
        logger.warning("画像の読み込みに失敗したためスタブ記述を返します: %s", error)
        return _stub_description(image_path)

    content_type = _CONTENT_TYPE_BY_SUFFIX.get(image_path.suffix.lower(), "image/jpeg")
    encoded = base64.b64encode(image_bytes).decode("ascii")

    url = (
        f"{settings.azure_openai_endpoint.rstrip('/')}/openai/deployments/"
        f"{settings.azure_openai_vision_deployment}/chat/completions"
        f"?api-version={settings.azure_openai_api_version}"
    )

    try:
        response = await request_with_retry(
            "POST",
            url,
            headers={"api-key": settings.azure_openai_api_key},
            json={
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": _VISION_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{content_type};base64,{encoded}"},
                            },
                        ],
                    }
                ],
                "max_tokens": 200,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except (httpx.HTTPError, KeyError, IndexError) as error:
        logger.warning("Azure OpenAI Vision呼び出しに失敗したためスタブ記述を返します: %s", error)
        return _stub_description(image_path)


def analyze_image(image_path: Path) -> str:
    """同期コンテキスト（既存呼び出し互換用）から画像解析を行う。

    未設定時は常にスタブを返すため同期のままで問題ない。設定済みの場合は
    内部でイベントループを起動してAPI呼び出しを行う。
    """
    if not _is_configured():
        return _stub_description(image_path)

    import asyncio

    return asyncio.run(analyze_image_async(image_path))
