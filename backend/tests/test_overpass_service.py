from app.services.overpass_service import _build_query


def test_build_query_includes_stop_sign_nodes() -> None:
    # 一時停止標識（highway=stop）を crossing/traffic_signals と同じ nodes クエリに含める。
    # 交差点判定は osm_data.nodes の近接有無だけを見るため、これにより
    # 一時停止のある交差点も自動的に「制御あり」として非加点になる。
    query = _build_query((32.74, 129.87, 32.75, 129.88))

    assert 'node[highway~"crossing|traffic_signals|stop"]' in query
    # way/nodeともに1回のクエリにまとまっていること（Overpassは1検索1回のみ）
    assert query.count("node[highway") == 1
    assert query.count("way[highway]") == 1
