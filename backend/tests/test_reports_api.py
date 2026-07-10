import io

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def _create_report(latitude: str = "32.7503", longitude: str = "129.8777") -> dict:
    response = client.post(
        "/api/reports",
        data={"latitude": latitude, "longitude": longitude},
        files=[("images", _fake_image())],
    )
    return response.json()


def _fake_image(name: str = "photo.jpg", content_type: str = "image/jpeg", size: int = 100):
    return (name, io.BytesIO(b"\xff" * size), content_type)


def test_create_report_success() -> None:
    response = client.post(
        "/api/reports",
        data={"latitude": "32.7503", "longitude": "129.8777", "comment": "見通しが悪い"},
        files=[("images", _fake_image())],
    )

    assert response.status_code == 201
    body = response.json()
    assert body["latitude"] == 32.7503
    assert body["longitude"] == 129.8777
    assert body["comment_user"] == "見通しが悪い"
    assert len(body["image_urls"]) == 1
    assert body["image_urls"][0].startswith("/uploads/")
    assert body["risk_score"] is not None
    assert body["status"] == "unconfirmed"
    assert body["source"] == "manual"


def test_create_report_requires_at_least_one_image() -> None:
    response = client.post(
        "/api/reports",
        data={"latitude": "32.7503", "longitude": "129.8777"},
        files=[],
    )

    assert response.status_code in (400, 422)


def test_create_report_rejects_unsupported_content_type() -> None:
    response = client.post(
        "/api/reports",
        data={"latitude": "32.7503", "longitude": "129.8777"},
        files=[("images", _fake_image(name="photo.gif", content_type="image/gif"))],
    )

    assert response.status_code == 400


def test_create_report_rejects_more_than_max_images() -> None:
    files = [("images", _fake_image(name=f"p{i}.jpg")) for i in range(settings.max_images_per_report + 1)]

    response = client.post(
        "/api/reports",
        data={"latitude": "32.7503", "longitude": "129.8777"},
        files=files,
    )

    assert response.status_code == 400


def test_create_report_rejects_oversized_image(monkeypatch) -> None:
    monkeypatch.setattr(settings, "max_image_size_bytes", 10)

    response = client.post(
        "/api/reports",
        data={"latitude": "32.7503", "longitude": "129.8777"},
        files=[("images", _fake_image(size=1000))],
    )

    assert response.status_code == 400


def test_list_reports_includes_created_report() -> None:
    create_response = client.post(
        "/api/reports",
        data={"latitude": "32.75", "longitude": "129.87"},
        files=[("images", _fake_image())],
    )
    created_id = create_response.json()["id"]

    list_response = client.get("/api/reports")

    assert list_response.status_code == 200
    ids = [r["id"] for r in list_response.json()]
    assert created_id in ids


def test_search_reports_filters_by_location_and_score() -> None:
    client.post(
        "/api/reports",
        data={"latitude": "32.70", "longitude": "129.80"},
        files=[("images", _fake_image())],
    )
    far_report = client.post(
        "/api/reports",
        data={"latitude": "40.0", "longitude": "140.0"},
        files=[("images", _fake_image())],
    ).json()

    nearby = client.get(
        "/api/reports/search", params={"lat": 32.70, "lng": 129.80, "radius_m": 1000}
    ).json()
    nearby_ids = [r["id"] for r in nearby]
    assert far_report["id"] not in nearby_ids


def test_similar_reports_endpoint_returns_list_structure() -> None:
    first = client.post(
        "/api/reports",
        data={"latitude": "32.70", "longitude": "129.80"},
        files=[("images", _fake_image())],
    ).json()
    client.post(
        "/api/reports",
        data={"latitude": "32.71", "longitude": "129.81"},
        files=[("images", _fake_image())],
    )

    response = client.get(f"/api/reports/{first['id']}/similar", params={"limit": 5})

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    for item in body:
        assert "report" in item
        assert "similarity" in item


def test_similar_reports_returns_empty_for_unknown_id() -> None:
    unknown_id = "00000000-0000-0000-0000-000000000000"

    response = client.get(f"/api/reports/{unknown_id}/similar")

    assert response.status_code == 200
    assert response.json() == []


def test_list_reports_filters_by_status(monkeypatch) -> None:
    monkeypatch.setattr(settings, "admin_token", "secret-token")

    report = _create_report()

    confirmed = client.patch(
        f"/api/reports/{report['id']}/status",
        json={"status": "confirmed"},
        headers={"X-Admin-Token": "secret-token"},
    ).json()
    assert confirmed["status"] == "confirmed"

    _create_report(latitude="32.71", longitude="129.81")  # unconfirmedのまま

    confirmed_only = client.get("/api/reports", params={"status": "confirmed"}).json()
    confirmed_ids = [r["id"] for r in confirmed_only]
    assert report["id"] in confirmed_ids
    assert all(r["status"] == "confirmed" for r in confirmed_only)

    unconfirmed_only = client.get("/api/reports", params={"status": "unconfirmed"}).json()
    assert report["id"] not in [r["id"] for r in unconfirmed_only]


def test_update_report_status_requires_admin_token_configured(monkeypatch) -> None:
    monkeypatch.setattr(settings, "admin_token", "")

    report = _create_report()

    response = client.patch(
        f"/api/reports/{report['id']}/status",
        json={"status": "confirmed"},
        headers={"X-Admin-Token": "anything"},
    )

    assert response.status_code == 401


def test_update_report_status_rejects_wrong_token(monkeypatch) -> None:
    monkeypatch.setattr(settings, "admin_token", "secret-token")

    report = _create_report()

    response = client.patch(
        f"/api/reports/{report['id']}/status",
        json={"status": "confirmed"},
        headers={"X-Admin-Token": "wrong-token"},
    )

    assert response.status_code == 401


def test_update_report_status_rejects_missing_token_header(monkeypatch) -> None:
    monkeypatch.setattr(settings, "admin_token", "secret-token")

    report = _create_report()

    response = client.patch(
        f"/api/reports/{report['id']}/status",
        json={"status": "confirmed"},
    )

    assert response.status_code == 401


def test_update_report_status_returns_404_for_unknown_report(monkeypatch) -> None:
    monkeypatch.setattr(settings, "admin_token", "secret-token")

    unknown_id = "00000000-0000-0000-0000-000000000000"

    response = client.patch(
        f"/api/reports/{unknown_id}/status",
        json={"status": "confirmed"},
        headers={"X-Admin-Token": "secret-token"},
    )

    assert response.status_code == 404


def test_update_report_status_returns_422_for_invalid_status(monkeypatch) -> None:
    monkeypatch.setattr(settings, "admin_token", "secret-token")

    report = _create_report()

    response = client.patch(
        f"/api/reports/{report['id']}/status",
        json={"status": "not-a-real-status"},
        headers={"X-Admin-Token": "secret-token"},
    )

    assert response.status_code == 422


def test_update_report_status_success_updates_and_persists(monkeypatch) -> None:
    monkeypatch.setattr(settings, "admin_token", "secret-token")

    report = _create_report()

    response = client.patch(
        f"/api/reports/{report['id']}/status",
        json={"status": "rejected"},
        headers={"X-Admin-Token": "secret-token"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == report["id"]
    assert body["status"] == "rejected"

    persisted = client.get("/api/reports").json()
    persisted_report = next(r for r in persisted if r["id"] == report["id"])
    assert persisted_report["status"] == "rejected"
