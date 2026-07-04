import asyncio

from app.models.route import RoutePoint
from app.services import accident_service, hazard_analysis_service
from app.services.overpass_service import OsmWay, OverpassData, OverpassError


def _straight_route(n_points: int = 5, step_deg: float = 0.0005) -> list[RoutePoint]:
    base_lat, base_lng = 32.7503, 129.8777
    return [
        RoutePoint(latitude=base_lat + step_deg * i, longitude=base_lng)
        for i in range(n_points)
    ]


def test_analyze_hazards_scores_and_filters(monkeypatch) -> None:
    route_points = _straight_route()

    async def fake_fetch(_points):
        way = OsmWay(
            id=1,
            tags={"highway": "primary", "sidewalk": "no"},
            geometry=[hazard_analysis_service.LatLng(p.latitude, p.longitude) for p in route_points],
        )
        return OverpassData(ways=[way], nodes=[])

    monkeypatch.setattr(hazard_analysis_service, "fetch_osm_features", fake_fetch)
    monkeypatch.setattr(accident_service, "count_near", lambda lat, lng, radius_m=50: 0)

    hazards = asyncio.run(hazard_analysis_service.analyze_hazards(route_points))

    assert len(hazards) >= 1
    for hazard in hazards:
        assert hazard.risk_score >= 2
        assert "歩道なし" in hazard.risk_factors


def test_analyze_hazards_clusters_nearby_points(monkeypatch) -> None:
    # 50m間隔サンプルの各点がすべて同じ危険道路上にあり、120m以内は統合されるはず
    route_points = _straight_route(n_points=6, step_deg=0.0004)

    async def fake_fetch(_points):
        way = OsmWay(
            id=1,
            tags={"highway": "trunk", "sidewalk": "no", "maxspeed": "60"},
            geometry=[hazard_analysis_service.LatLng(p.latitude, p.longitude) for p in route_points],
        )
        return OverpassData(ways=[way], nodes=[])

    monkeypatch.setattr(hazard_analysis_service, "fetch_osm_features", fake_fetch)
    monkeypatch.setattr(accident_service, "count_near", lambda lat, lng, radius_m=50: 3)

    hazards = asyncio.run(hazard_analysis_service.analyze_hazards(route_points))

    # 候補点はサンプリング間隔的に複数生成されるが、40m以内は統合され件数が抑えられる
    assert len(hazards) >= 1
    assert all(h.risk_score == 5 for h in hazards)


def test_analyze_hazards_falls_back_to_accident_only_on_overpass_error(monkeypatch) -> None:
    route_points = _straight_route()

    async def failing_fetch(_points):
        raise OverpassError("network down")

    monkeypatch.setattr(hazard_analysis_service, "fetch_osm_features", failing_fetch)
    monkeypatch.setattr(accident_service, "count_near", lambda lat, lng, radius_m=50: 3)

    hazards = asyncio.run(hazard_analysis_service.analyze_hazards(route_points))

    # OSMタグがなくても事故件数のみでスコアされ、閾値を超えれば結果に残る
    assert len(hazards) >= 1
    for hazard in hazards:
        assert hazard.osm_tags == {}
        assert any("事故多発" in f for f in hazard.risk_factors)


def test_analyze_hazards_empty_route_returns_empty() -> None:
    assert asyncio.run(hazard_analysis_service.analyze_hazards([])) == []


def test_cluster_merges_accident_factor_without_duplicates(monkeypatch) -> None:
    # サンプル点ごとに事故件数が異なっても、クラスタ統合後は
    # 「事故多発（N件）」のような要因が1つだけになること（重複表現の回帰防止）
    route_points = _straight_route(n_points=4, step_deg=0.0003)

    async def fake_fetch(_points):
        way = OsmWay(
            id=1,
            tags={"highway": "tertiary"},
            geometry=[hazard_analysis_service.LatLng(p.latitude, p.longitude) for p in route_points],
        )
        return OverpassData(ways=[way], nodes=[])

    counts_by_lat = {}

    def fake_count_near(lat, lng, radius_m=50):
        # 各サンプル点ごとに異なる件数を返す
        key = round(lat, 6)
        counts_by_lat.setdefault(key, len(counts_by_lat) + 3)
        return counts_by_lat[key]

    monkeypatch.setattr(hazard_analysis_service, "fetch_osm_features", fake_fetch)
    monkeypatch.setattr(accident_service, "count_near", fake_count_near)

    hazards = asyncio.run(hazard_analysis_service.analyze_hazards(route_points))

    for hazard in hazards:
        accident_factors = [f for f in hazard.risk_factors if "事故多発" in f or "過去事故あり" in f]
        assert len(accident_factors) <= 1


def test_long_route_does_not_produce_excessive_pins(monkeypatch) -> None:
    # 回帰テスト: CLUSTER_RADIUS_M(120) > SAMPLE_INTERVAL_M(50) であること、および
    # 約1.3kmの全区間が危険道路のルートでもピンが乱立しないこと。
    # （半径40m時代は隣接50mサンプルが一切統合されず、1.3kmで22個返っていた）
    assert (
        hazard_analysis_service.CLUSTER_RADIUS_M > hazard_analysis_service.SAMPLE_INTERVAL_M
    )

    # 0.0005度 ≈ 55m × 24区間 ≈ 1.3km
    route_points = _straight_route(n_points=25, step_deg=0.0005)

    async def fake_fetch(_points):
        way = OsmWay(
            id=1,
            tags={"highway": "primary", "sidewalk": "no"},
            geometry=[hazard_analysis_service.LatLng(p.latitude, p.longitude) for p in route_points],
        )
        return OverpassData(ways=[way], nodes=[])

    monkeypatch.setattr(hazard_analysis_service, "fetch_osm_features", fake_fetch)
    monkeypatch.setattr(accident_service, "count_near", lambda lat, lng, radius_m=50: 1)

    hazards = asyncio.run(hazard_analysis_service.analyze_hazards(route_points))

    # 全サンプル（約27点）が候補になる最悪ケースでも、統合により10個以下に収まる
    assert 1 <= len(hazards) <= 10


def _parallel_ways_point_and_geometry():
    # 南北方向の直線道路。約5m東に対向車線の平行wayがある想定（ノードは共有しない）
    point = hazard_analysis_service.LatLng(32.7503, 129.8777)
    lats = [32.7498, 32.7503, 32.7508]
    west_geom = [hazard_analysis_service.LatLng(lat, 129.8777) for lat in lats]
    east_geom = [hazard_analysis_service.LatLng(lat, 129.87775) for lat in lats]
    return point, west_geom, east_geom


def _crossing_geometry():
    # (32.7503, 129.8777) を共有ノードとして東西方向に交差する道路
    return [
        hazard_analysis_service.LatLng(32.7503, 129.8772),
        hazard_analysis_service.LatLng(32.7503, 129.8777),
        hazard_analysis_service.LatLng(32.7503, 129.8782),
    ]


def test_parallel_oneway_pair_with_same_name_is_not_intersection() -> None:
    # 回帰テスト: 国道の oneway 対向車線ペア（同名の平行way 2本）を
    # 「信号・横断歩道のない交差点」と誤検出しないこと
    point, west_geom, east_geom = _parallel_ways_point_and_geometry()
    osm_data = OverpassData(
        ways=[
            OsmWay(id=1, tags={"highway": "primary", "name": "国道34号", "oneway": "yes"}, geometry=west_geom),
            OsmWay(id=2, tags={"highway": "primary", "name": "国道34号", "oneway": "yes"}, geometry=east_geom),
        ],
        nodes=[],
    )

    assert hazard_analysis_service._has_uncontrolled_intersection(point, osm_data) is False


def test_parallel_ways_with_same_ref_and_no_name_is_not_intersection() -> None:
    # nameが無くてもrefが同じなら同一道路とみなす
    point, west_geom, east_geom = _parallel_ways_point_and_geometry()
    osm_data = OverpassData(
        ways=[
            OsmWay(id=1, tags={"highway": "primary", "ref": "34"}, geometry=west_geom),
            OsmWay(id=2, tags={"highway": "primary", "ref": "34"}, geometry=east_geom),
        ],
        nodes=[],
    )

    assert hazard_analysis_service._has_uncontrolled_intersection(point, osm_data) is False


def test_crossing_ways_with_different_names_are_detected_as_intersection() -> None:
    # 名前の異なる2本の道路がノードを共有して交差し、信号・横断歩道が無ければ検出する
    point, west_geom, _ = _parallel_ways_point_and_geometry()
    osm_data = OverpassData(
        ways=[
            OsmWay(id=1, tags={"highway": "primary", "name": "国道34号"}, geometry=west_geom),
            OsmWay(id=2, tags={"highway": "residential", "name": "寺町通り"}, geometry=_crossing_geometry()),
        ],
        nodes=[],
    )

    assert hazard_analysis_service._has_uncontrolled_intersection(point, osm_data) is True


def test_parallel_ways_with_different_names_but_no_shared_node_are_not_intersection() -> None:
    # 回帰テスト: 名前が異なっていてもノードを共有しない並走道路（並行する別道路）は
    # 交差点として検出しない
    point, west_geom, east_geom = _parallel_ways_point_and_geometry()
    osm_data = OverpassData(
        ways=[
            OsmWay(id=1, tags={"highway": "primary", "name": "国道34号"}, geometry=west_geom),
            OsmWay(id=2, tags={"highway": "residential", "name": "寺町通り"}, geometry=east_geom),
        ],
        nodes=[],
    )

    assert hazard_analysis_service._has_uncontrolled_intersection(point, osm_data) is False


def test_crossing_footway_does_not_count_as_intersection() -> None:
    # 回帰テスト: 別wayとして登録された歩道・階段・敷地内通路（highway=footway等）は
    # 車道と交差していても「2本目の道路」と数えず、交差点と誤検出しないこと
    point, west_geom, _ = _parallel_ways_point_and_geometry()
    osm_data = OverpassData(
        ways=[
            OsmWay(id=1, tags={"highway": "trunk", "name": "市役所通り"}, geometry=west_geom),
            OsmWay(id=2, tags={"highway": "footway"}, geometry=_crossing_geometry()),
            OsmWay(id=3, tags={"highway": "steps"}, geometry=_crossing_geometry()),
            OsmWay(id=4, tags={"highway": "service"}, geometry=_crossing_geometry()),
        ],
        nodes=[],
    )

    assert hazard_analysis_service._has_uncontrolled_intersection(point, osm_data) is False


def test_unnamed_crossing_ways_fall_back_to_way_id_grouping() -> None:
    # name/refが両方無い場合はway idでグループ化され、ノードを共有して交差する
    # 2本があれば交差点候補になる
    point, west_geom, _ = _parallel_ways_point_and_geometry()
    osm_data = OverpassData(
        ways=[
            OsmWay(id=1, tags={"highway": "residential"}, geometry=west_geom),
            OsmWay(id=2, tags={"highway": "residential"}, geometry=_crossing_geometry()),
        ],
        nodes=[],
    )

    assert hazard_analysis_service._has_uncontrolled_intersection(point, osm_data) is True


def test_unnamed_parallel_ways_without_shared_node_are_not_intersection() -> None:
    # 回帰テスト: 無名のoneway対向車線ペア（ノード非共有の平行way）を誤検出しない
    point, west_geom, east_geom = _parallel_ways_point_and_geometry()
    osm_data = OverpassData(
        ways=[
            OsmWay(id=1, tags={"highway": "tertiary", "oneway": "yes"}, geometry=west_geom),
            OsmWay(id=2, tags={"highway": "tertiary", "oneway": "yes"}, geometry=east_geom),
        ],
        nodes=[],
    )

    assert hazard_analysis_service._has_uncontrolled_intersection(point, osm_data) is False
