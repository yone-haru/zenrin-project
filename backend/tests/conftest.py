"""全テスト共通のフィクスチャ。

本番用の `backend/data/app.db` や `backend/uploads/` をテストで汚さないよう、
DB接続・事故データインデックス・画像アップロード先を毎テストごとにtmp_pathへ
差し替える。これによりpytestは完全にオフライン・副作用なしで実行できる。
"""

from __future__ import annotations

import pytest

from app.core import database as database_module
from app.services import accident_service
from app.services import image_storage


@pytest.fixture(autouse=True)
def isolate_backend_data(tmp_path, monkeypatch):
    db_path = tmp_path / "app.db"
    database_module.reset_connection_for_tests(db_path)

    accident_service.reset_index_for_tests(tmp_path / "accidents_not_present.csv")

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(exist_ok=True)
    monkeypatch.setattr(image_storage, "UPLOAD_DIR", upload_dir)

    yield
