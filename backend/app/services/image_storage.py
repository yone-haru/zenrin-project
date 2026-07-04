import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}

_EXTENSION_BY_CONTENT_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


class ImageValidationError(ValueError):
    """アップロード画像がサイズ・枚数制限を超えた場合のエラー。"""


def validate_images(files: list[UploadFile]) -> None:
    if not files:
        raise ImageValidationError("画像を1枚以上添付してください")

    if len(files) > settings.max_images_per_report:
        raise ImageValidationError(
            f"画像は最大{settings.max_images_per_report}枚まで添付できます"
        )

    for file in files:
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise ImageValidationError(f"対応していないファイル形式です: {file.content_type}")


def save_images(report_id: str, files: list[UploadFile]) -> list[str]:
    """画像を保存し、公開URLの一覧を返す。

    拡張子はアップロードされたファイル名ではなく `content_type` から決定する
    （ファイル名の拡張子は信頼できないため）。1枚あたり `max_image_size_bytes` を
    超える場合はエラーとする。
    """
    report_dir = UPLOAD_DIR / report_id
    report_dir.mkdir(parents=True, exist_ok=True)

    image_urls = []
    for file in files:
        extension = _EXTENSION_BY_CONTENT_TYPE.get(file.content_type or "", ".jpg")
        filename = f"{uuid.uuid4()}{extension}"
        destination = report_dir / filename

        content = file.file.read()
        if len(content) > settings.max_image_size_bytes:
            max_mb = settings.max_image_size_bytes / (1024 * 1024)
            raise ImageValidationError(f"画像サイズは1枚あたり{max_mb:.0f}MB以下にしてください")

        with destination.open("wb") as out_file:
            out_file.write(content)
        image_urls.append(f"/uploads/{report_id}/{filename}")

    return image_urls


def url_to_path(image_url: str) -> Path:
    relative = image_url.removeprefix("/uploads/")
    return UPLOAD_DIR / relative
