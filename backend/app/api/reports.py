from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.geo import haversine_distance_m
from app.core.storage import load_reports, save_reports
from app.models.report import Report, SimilarReport
from app.services.embedding_service import generate_embedding
from app.services.image_storage import ALLOWED_CONTENT_TYPES, save_images, url_to_path
from app.services.scoring_service import aggregate_nearby_scores, calculate_risk_score
from app.services.search_service import find_similar_report_ids, index_report
from app.services.vision_service import analyze_image

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("", response_model=list[Report])
def list_reports() -> list[Report]:
    return load_reports()


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


@router.post("", response_model=Report, status_code=201)
async def create_report(
    latitude: Annotated[float, Form()],
    longitude: Annotated[float, Form()],
    images: Annotated[list[UploadFile], File()],
    comment: Annotated[str | None, Form()] = None,
) -> Report:
    if not images:
        raise HTTPException(status_code=400, detail="画像を1枚以上添付してください")

    for image in images:
        if image.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"対応していないファイル形式です: {image.content_type}",
            )

    report_id = uuid4()
    image_urls = save_images(str(report_id), images)

    descriptions = [analyze_image(url_to_path(url)) for url in image_urls]
    description_ai = " / ".join(descriptions)
    vector = generate_embedding(description_ai)
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
