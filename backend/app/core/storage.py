import json
from pathlib import Path

from app.models.report import Report

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DATA_FILE = DATA_DIR / "reports.json"


def _ensure_data_file() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]", encoding="utf-8")


def load_reports() -> list[Report]:
    _ensure_data_file()
    raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return [Report.model_validate(item) for item in raw]


def save_reports(reports: list[Report]) -> None:
    _ensure_data_file()
    DATA_FILE.write_text(
        json.dumps(
            [json.loads(r.model_dump_json()) for r in reports],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
