from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.config import settings
from app.core.geo import haversine_distance_m
from app.core.storage import load_reports, save_report, save_reports
from app.models.report import Report, ReportStatus, SimilarReport
from app.services.embedding_service import generate_embedding_async
from app.services.image_storage import ImageValidationError, save_images, url_to_path, validate_images
from app.services.scoring_service import aggregate_nearby_scores, calculate_risk_score
from app.services.search_service import find_similar_report_ids, index_report
from app.services.vision_service import analyze_image_async

router = APIRouter(prefix="/api/reports", tags=["reports"])


class ReportStatusUpdate(BaseModel):
    status: ReportStatus


@router.get("", response_model=list[Report])
def list_reports(status: ReportStatus | None = None) -> list[Report]:
    reports = load_reports()
    if status is not None:
        reports = [r for r in reports if r.status == status]
    return reports


@router.get("/search", response_model=list[Report])
def search_reports(
    keyword: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    radius_m: float = 500,
    min_risk_score: int | None = None,
) -> list[Report]:
    reports = load_reports()

    if keyword:
        reports = [r for r in reports if r.description_ai and keyword in r.description_ai]

    if lat is not None and lng is not None:
        reports = [
            r
            for r in reports
            if haversine_distance_m(lat, lng, r.latitude, r.longitude) <= radius_m
        ]

    if min_risk_score is not None:
        reports = [r for r in reports if (r.risk_score or 0) >= min_risk_score]

    return reports


@router.get("/{report_id}/similar", response_model=list[SimilarReport])
def get_similar_reports(report_id: UUID, limit: int = 5) -> list[SimilarReport]:
    similar_ids = find_similar_report_ids(report_id, limit)
    reports_by_id = {r.id: r for r in load_reports()}

    return [
        SimilarReport(report=reports_by_id[similar_id], similarity=similarity)
        for similar_id, similarity in similar_ids
        if similar_id in reports_by_id
    ]


@router.patch("/{report_id}/status", response_model=Report)
def update_report_status(
    report_id: UUID,
    body: ReportStatusUpdate,
    x_admin_token: Annotated[str | None, Header(alias="X-Admin-Token")] = None,
) -> Report:
    """通報のステータスを更新する（自治体職員向け管理API）。

    admin_token が未設定（空文字）の場合はヘッダーの値に関わらず常に401を返す。
    """
    if not settings.admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="管理者トークンが無効です")

    reports_by_id = {r.id: r for r in load_reports()}
    report = reports_by_id.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="通報が見つかりません")

    report.status = body.status
    save_report(report)
    return report


@router.post("", response_model=Report, status_code=201)
async def create_report(
    latitude: Annotated[float, Form()],
    longitude: Annotated[float, Form()],
    images: Annotated[list[UploadFile], File()],
    comment: Annotated[str | None, Form()] = None,
) -> Report:
    try:
        validate_images(images)
        report_id = uuid4()
        image_urls = save_images(str(report_id), images)
    except ImageValidationError as error:
        raise HTTPException(status_code=400, detail=str(error))

    descriptions = [await analyze_image_async(url_to_path(url)) for url in image_urls]
    description_ai = " / ".join(descriptions)
    vector = await generate_embedding_async(description_ai)
    index_report(report_id, description_ai, vector)

    risk_score = calculate_risk_score(description_ai)
    report = Report(
        id=report_id,
        latitude=latitude,
        longitude=longitude,
        image_urls=image_urls,
        description_ai=description_ai,
        risk_score=risk_score,
        comment_user=comment,
    )

    existing_reports = load_reports()
    updated_cluster = aggregate_nearby_scores(report, existing_reports)

    reports_by_id = {r.id: r for r in existing_reports}
    for updated in updated_cluster:
        reports_by_id[updated.id] = updated
    save_reports(list(reports_by_id.values()))

    return report
