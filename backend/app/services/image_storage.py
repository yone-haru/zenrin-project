import uuid
from pathlib import Path

from fastapi import UploadFile

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}


def save_images(report_id: str, files: list[UploadFile]) -> list[str]:
    report_dir = UPLOAD_DIR / report_id
    report_dir.mkdir(parents=True, exist_ok=True)

    image_urls = []
    for file in files:
        extension = Path(file.filename or "").suffix or ".jpg"
        filename = f"{uuid.uuid4()}{extension}"
        destination = report_dir / filename
        with destination.open("wb") as out_file:
            out_file.write(file.file.read())
        image_urls.append(f"/uploads/{report_id}/{filename}")

    return image_urls


def url_to_path(image_url: str) -> Path:
    relative = image_url.removeprefix("/uploads/")
    return UPLOAD_DIR / relative
