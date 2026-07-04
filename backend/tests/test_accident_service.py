from app.services.accident_service import AccidentGridIndex


def _write_csv(path, rows) -> None:
    lines = ["year,latitude,longitude,death_count,injury_count,accident_type"]
    for row in rows:
        lines.append(",".join(str(v) for v in row))
    path.write_text("\n".join(lines), encoding="utf-8")


def test_count_near_finds_points_within_radius(tmp_path) -> None:
    csv_path = tmp_path / "accidents.csv"
    _write_csv(
        csv_path,
        [
            (2023, 32.7503, 129.8777, 0, 1, "車両相互"),
            (2023, 32.7504, 129.8778, 0, 1, "車両相互"),  # 数十m以内
            (2023, 33.0, 130.0, 0, 1, "車両相互"),  # 遠方
        ],
    )

    index = AccidentGridIndex()
    index.load(csv_path)

    assert index.count == 3
    assert index.count_near(32.7503, 129.8777, radius_m=50) == 2
    assert index.count_near(32.7503, 129.8777, radius_m=1) == 1


def test_count_near_returns_zero_when_file_missing(tmp_path) -> None:
    index = AccidentGridIndex()
    index.load(tmp_path / "does_not_exist.csv")

    assert index.count == 0
    assert index.count_near(32.75, 129.87) == 0


def test_ignores_leading_comment_line(tmp_path) -> None:
    csv_path = tmp_path / "accidents.csv"
    csv_path.write_text(
        "# 仮定: サンプルデータ\n"
        "year,latitude,longitude,death_count,injury_count,accident_type\n"
        "2023,32.75,129.87,0,1,車両相互\n",
        encoding="utf-8",
    )

    index = AccidentGridIndex()
    index.load(csv_path)

    assert index.count == 1


def test_grid_cell_boundary_still_found_via_neighbor_cells(tmp_path) -> None:
    # グリッドセルの境界をまたぐケースでも近傍3x3セル探索で拾えること
    csv_path = tmp_path / "accidents.csv"
    _write_csv(csv_path, [(2023, 32.7500, 129.8700, 0, 1, "車両相互")])

    index = AccidentGridIndex()
    index.load(csv_path)

    # 境界のすぐ外側の座標から検索しても見つかる
    assert index.count_near(32.7499, 129.8699, radius_m=50) == 1
