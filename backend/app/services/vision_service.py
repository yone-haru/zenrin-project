import random
from pathlib import Path

from app.core.config import settings

_STUB_DESCRIPTIONS = [
    "ガードレールがなく、車道との境界が不明確である。",
    "見通しの悪いカーブがあり、対向車や人の存在に気づきにくい。",
    "街灯が少なく、夜間は視認性が低い。",
    "歩道が狭く、児童が車道側に寄って歩く必要がある。",
    "交差点の見通しが悪く、出会い頭の危険がある。",
]


def analyze_image(image_path: Path) -> str:
    """画像から危険要因の記述を生成する。

    Azure OpenAI（GPT-4o Vision）の認証情報が未設定の間はスタブとして
    固定候補からランダムに記述を返す。認証情報を設定後、実際のAPI呼び出しに差し替える。
    """
    if not settings.azure_openai_api_key:
        return random.choice(_STUB_DESCRIPTIONS)

    raise NotImplementedError("Azure OpenAI（GPT-4o Vision）連携は未実装です")
