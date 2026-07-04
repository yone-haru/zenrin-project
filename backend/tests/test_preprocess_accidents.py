import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.preprocess_accidents import convert_row, dms_to_decimal, in_bbox  # noqa: E402


def test_dms_to_decimal_latitude() -> None:
    # 43度10分07.628秒 -> 43 + 10/60 + 7.628/3600
    result = dms_to_decimal("431007628", degree_digits=2)
    expected = 43 + 10 / 60 + 7.628 / 3600
    assert abs(result - expected) < 1e-9


def test_dms_to_decimal_longitude() -> None:
    # 141度03分28.320秒
    result = dms_to_decimal("1410328320", degree_digits=3)
    expected = 141 + 3 / 60 + 28.320 / 3600
    assert abs(result - expected) < 1e-9


def test_in_bbox_true_and_false() -> None:
    bbox = (32.4, 34.8, 128.3, 130.5)
    assert in_bbox(32.75, 129.87, bbox) is True
    assert in_bbox(43.0, 141.0, bbox) is False


def test_convert_row_extracts_expected_fields() -> None:
    row = [""] * 68
    row[4] = "2"  # 事故内容: 負傷事故
    row[5] = "0"  # 死者数
    row[6] = "2"  # 負傷者数
    row[10] = "2023"  # 発生日時 年
    row[35] = "21"  # 事故類型: 車両相互
    row[60] = "431007628"
    row[61] = "1410328320"

    converted = convert_row(row)

    assert converted is not None
    assert converted["year"] == "2023"
    assert converted["death_count"] == 0
    assert converted["injury_count"] == 2
    assert converted["accident_type"] == "車両相互"
    assert abs(converted["latitude"] - (43 + 10 / 60 + 7.628 / 3600)) < 1e-9
    assert abs(converted["longitude"] - (141 + 3 / 60 + 28.320 / 3600)) < 1e-9


def test_convert_row_returns_none_for_missing_coordinates() -> None:
    row = [""] * 68
    row[60] = "000000000"
    row[61] = "0000000000"

    assert convert_row(row) is None
