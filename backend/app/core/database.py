"""SQLite永続化層（標準ライブラリ sqlite3 のみを使用）。

- WALモードで並行読み書きの安全性を確保する。
- reports / vectors の2テーブルを保持する。
- 起動時に旧 `data/reports.json` が存在すればレコードを移行し、
  移行済みファイルは `.migrated` にリネームする（多重移行防止）。

このモジュールはプロセス内シングルトンの sqlite3.Connection を保持し、
`threading.Lock` で書き込みを直列化する（開発規模のトラフィックを想定した
シンプルな実装。将来的な高負荷対応が必要になればコネクションプール等へ移行する）。
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DB_FILE = DATA_DIR / "app.db"
LEGACY_REPORTS_FILE = DATA_DIR / "reports.json"

_lock = threading.Lock()
_connection: sqlite3.Connection | None = None


SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    image_urls TEXT NOT NULL,
    description_ai TEXT,
    risk_score INTEGER,
    comment_user TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    source TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reports_lat_lng ON reports (latitude, longitude);

CREATE TABLE IF NOT EXISTS vectors (
    report_id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    vector TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def get_connection() -> sqlite3.Connection:
    global _connection
    if _connection is None:
        with _lock:
            if _connection is None:
                _connection = _connect()
                _migrate_legacy_reports(_connection)
    return _connection


def reset_connection_for_tests(db_path: Path) -> sqlite3.Connection:
    """テスト用に別ファイル（tmp_path等）へ接続を差し替える。"""
    global _connection, DB_FILE, DATA_DIR
    DB_FILE = db_path
    DATA_DIR = db_path.parent
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if _connection is not None:
        _connection.close()
    _connection = _connect()
    return _connection


def _migrate_legacy_reports(conn: sqlite3.Connection) -> None:
    """旧 reports.json が存在すれば reports テーブルへ取り込む。"""
    if not LEGACY_REPORTS_FILE.exists():
        return

    try:
        raw = json.loads(LEGACY_REPORTS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        logger.warning("reports.json の読み込みに失敗したため移行をスキップします: %s", error)
        return

    if not raw:
        LEGACY_REPORTS_FILE.rename(LEGACY_REPORTS_FILE.with_suffix(".json.migrated"))
        return

    with _lock:
        cursor = conn.cursor()
        migrated = 0
        for item in raw:
            cursor.execute(
                """
                INSERT OR IGNORE INTO reports
                    (id, latitude, longitude, image_urls, description_ai,
                     risk_score, comment_user, status, created_at, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(item["id"]),
                    item["latitude"],
                    item["longitude"],
                    json.dumps(item.get("image_urls", []), ensure_ascii=False),
                    item.get("description_ai"),
                    item.get("risk_score"),
                    item.get("comment_user"),
                    item.get("status", "unconfirmed"),
                    item.get("created_at"),
                    item.get("source", "manual"),
                ),
            )
            migrated += cursor.rowcount
        conn.commit()

    logger.info("reports.json から %d 件を SQLite へ移行しました", migrated)
    LEGACY_REPORTS_FILE.rename(LEGACY_REPORTS_FILE.with_suffix(".json.migrated"))


def check_health() -> bool:
    """DB疎通確認用。正常なら True。"""
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        return True
    except sqlite3.Error:
        return False
