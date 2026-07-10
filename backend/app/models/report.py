from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ReportStatus(str, Enum):
    UNCONFIRMED = "unconfirmed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class ReportSource(str, Enum):
    MANUAL = "manual"
    STREETVIEW = "streetview"


class Report(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    latitude: float
    longitude: float
    image_urls: list[str]
    description_ai: str | None = None
    risk_score: int | None = None
    comment_user: str | None = None
    status: ReportStatus = ReportStatus.UNCONFIRMED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source: ReportSource = ReportSource.MANUAL


class SimilarReport(BaseModel):
    report: Report
    similarity: float
