from app.services.scoring_service import calculate_hazard_score


def test_no_factors_scores_minimum() -> None:
    score, factors = calculate_hazard_score({}, accident_count=0)
    assert score == 1
    assert factors == []


def test_no_sidewalk_adds_two() -> None:
    score, factors = calculate_hazard_score({"sidewalk": "no"}, accident_count=0)
    assert score == 2
    assert "歩道なし" in factors


def test_primary_highway_adds_two() -> None:
    score, factors = calculate_hazard_score({"highway": "primary"}, accident_count=0)
    assert score == 2
    assert any("幹線道路" in f for f in factors)


def test_secondary_highway_adds_one() -> None:
    score, factors = calculate_hazard_score({"highway": "secondary"}, accident_count=0)
    assert score == 1


def test_high_maxspeed_adds_one() -> None:
    score, factors = calculate_hazard_score({"maxspeed": "60"}, accident_count=0)
    assert score == 1
    assert any("60" in f for f in factors)


def test_low_maxspeed_does_not_add() -> None:
    score, factors = calculate_hazard_score({"maxspeed": "30"}, accident_count=0)
    assert score == 1
    assert factors == []


def test_uncontrolled_intersection_adds_one() -> None:
    score, factors = calculate_hazard_score({}, accident_count=0, has_uncontrolled_intersection=True)
    assert score == 1
    assert "信号・横断歩道のない交差点" in factors


def test_one_or_two_accidents_adds_one() -> None:
    score, factors = calculate_hazard_score({}, accident_count=1)
    assert score == 1
    assert any("過去事故あり" in f for f in factors)


def test_many_accidents_adds_two() -> None:
    score, factors = calculate_hazard_score({}, accident_count=3)
    assert score == 2
    assert any("事故多発" in f and "3件" in f for f in factors)


def test_score_clamped_to_max_five() -> None:
    score, factors = calculate_hazard_score(
        {"highway": "primary", "sidewalk": "no", "maxspeed": "60"},
        accident_count=5,
        has_uncontrolled_intersection=True,
    )
    assert score == 5


def test_complex_intersection_adds_one() -> None:
    score, factors = calculate_hazard_score({}, accident_count=0, complex_intersection=True)
    assert score == 1
    assert "複雑な交差点（五差路など）" in factors


def test_sharp_curve_adds_one() -> None:
    score, factors = calculate_hazard_score({}, accident_count=0, sharp_curve=True)
    assert score == 1
    assert "急カーブ" in factors


def test_complex_intersection_is_independent_of_uncontrolled_intersection() -> None:
    # 信号があっても（has_uncontrolled_intersection=False）、道路の合流本数が
    # 多ければ複雑な交差点として別枠で加点される
    score, factors = calculate_hazard_score(
        {},
        accident_count=0,
        has_uncontrolled_intersection=False,
        complex_intersection=True,
    )
    assert score == 1
    assert "信号・横断歩道のない交差点" not in factors
    assert "複雑な交差点（五差路など）" in factors


def test_all_new_factors_clamped_to_max_five() -> None:
    score, factors = calculate_hazard_score(
        {"highway": "primary", "sidewalk": "no", "maxspeed": "60"},
        accident_count=5,
        has_uncontrolled_intersection=True,
        complex_intersection=True,
        sharp_curve=True,
    )
    assert score == 5
    assert "複雑な交差点（五差路など）" in factors
    assert "急カーブ" in factors
