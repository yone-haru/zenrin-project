import json
import sqlite3
import threading

from app.core.database import get_connection
from app.models.report import Report

_write_lock = threading.Lock()


def _row_to_report(row: sqlite3.Row) -> Report:
    return Report.model_validate(
        {
            "id": row["id"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "image_urls": json.loads(row["image_urls"]),
            "description_ai": row["description_ai"],
            "risk_score": row["risk_score"],
            "comment_user": row["comment_user"],
            "status": row["status"],
            "created_at": row["created_at"],
            "source": row["source"],
        }
    )


def load_reports() -> list[Report]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM reports ORDER BY created_at DESC").fetchall()
    return [_row_to_report(row) for row in rows]


def save_report(report: Report) -> None:
    """1件のレポートを挿入または更新する。"""
    conn = get_connection()
    with _write_lock:
        conn.execute(
            """
            INSERT INTO reports
                (id, latitude, longitude, image_urls, description_ai,
                 risk_score, comment_user, status, created_at, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                latitude=excluded.latitude,
                longitude=excluded.longitude,
                image_urls=excluded.image_urls,
                description_ai=excluded.description_ai,
                risk_score=excluded.risk_score,
                comment_user=excluded.comment_user,
                status=excluded.status,
                created_at=excluded.created_at,
                source=excluded.source
            """,
            (
                str(report.id),
                report.latitude,
                report.longitude,
                json.dumps(report.image_urls, ensure_ascii=False),
                report.description_ai,
                report.risk_score,
                report.comment_user,
                report.status.value,
                report.created_at.isoformat(),
                report.source.value,
            ),
        )
        conn.commit()


def save_reports(reports: list[Report]) -> None:
    """複数件のレポートをまとめて挿入・更新する（既存の他レコードには影響しない）。"""
    for report in reports:
        save_report(report)
