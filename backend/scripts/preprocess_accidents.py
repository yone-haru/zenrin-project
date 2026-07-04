"""警察庁 交通事故オープンデータ（本票 / honhyo CSV）前処理スクリプト。

データ出典: 警察庁 交通事故統計情報オープンデータ
https://www.npa.go.jp/publications/statistics/koutsuu/opendata/index_opendata.html
例: https://www.npa.go.jp/publications/statistics/koutsuu/opendata/2023/honhyo_2023.csv

honhyo CSV は CP932（Shift_JIS系）でエンコードされ、事故地点の緯度・経度は
度分秒を詰めた固定長の数値文字列で格納されている。
  - 緯度（北緯）: 9桁 = 度2桁 + 分2桁 + 秒2桁 + 秒の小数部3桁 (DDMMSSsss)
  - 経度（東経）: 10桁 = 度3桁 + 分2桁 + 秒2桁 + 秒の小数部3桁 (DDDMMSSsss)

このスクリプトは、上記の生CSV（数万〜数十万行、Git管理対象外）を読み込み、
指定bbox（デフォルトは長崎県周辺）でフィルタし、アプリが利用する
`backend/data/accidents.csv`（year,latitude,longitude,death_count,injury_count,accident_type）
を生成する。

使い方:
    python scripts/preprocess_accidents.py [--input data/raw/honhyo_2023.csv ...] \
        [--output data/accidents.csv] \
        [--bbox 32.4 34.8 128.3 130.5]

実データが取得できない環境向けに `--sample` オプションで現実的なサンプルデータ
（仮定: サンプルデータ）を生成することもできる。
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
DEFAULT_OUTPUT = BACKEND_DIR / "data" / "accidents.csv"
DEFAULT_RAW = BACKEND_DIR / "data" / "raw" / "honhyo_2023.csv"

# 長崎県周辺bbox（南西諸島の一部離島は含まないおおよその範囲）
DEFAULT_BBOX = (32.4, 34.8, 128.3, 130.5)  # (min_lat, max_lat, min_lng, max_lng)

# 事故内容（列4）: 1=死亡事故, 2=負傷事故（人身事故）
ACCIDENT_CONTENT_MAP = {
    "1": "死亡事故",
    "2": "負傷事故",
}

# 事故類型（列35）の大分類コード
ACCIDENT_TYPE_MAP = {
    "01": "人対車両",
    "21": "車両相互",
    "41": "車両単独",
    "61": "踏切",
}

COL_DEATH_COUNT = 5
COL_INJURY_COUNT = 6
COL_YEAR = 10
COL_ACCIDENT_CONTENT = 4
COL_ACCIDENT_TYPE = 35
COL_LATITUDE = 60
COL_LONGITUDE = 61


def dms_to_decimal(raw: str, degree_digits: int) -> float:
    """警察庁形式の度分秒詰め込み文字列を10進度に変換する。

    degree_digits: 度の桁数（緯度=2, 経度=3）
    残り7桁は 分2桁 + 秒2桁 + 秒の小数部3桁 固定。
    """
    total_len = degree_digits + 7
    raw = raw.strip().zfill(total_len)
    degree = int(raw[:degree_digits])
    minute = int(raw[degree_digits : degree_digits + 2])
    second = int(raw[degree_digits + 2 : degree_digits + 4])
    second_frac = int(raw[degree_digits + 4 : degree_digits + 7])
    seconds = second + second_frac / 1000
    return degree + minute / 60 + seconds / 3600


def _is_missing(raw: str) -> bool:
    if not raw:
        return True
    stripped = raw.strip()
    if stripped == "":
        return True
    # 全桁0または全桁9は「データなし」を示す慣例値
    return set(stripped) in ({"0"}, {"9"})


def convert_row(row: list[str]) -> dict | None:
    try:
        lat_raw = row[COL_LATITUDE]
        lng_raw = row[COL_LONGITUDE]
        if _is_missing(lat_raw) or _is_missing(lng_raw):
            return None
        latitude = dms_to_decimal(lat_raw, 2)
        longitude = dms_to_decimal(lng_raw, 3)
        year = row[COL_YEAR]
        death_count = int(row[COL_DEATH_COUNT] or 0)
        injury_count = int(row[COL_INJURY_COUNT] or 0)
        content_code = row[COL_ACCIDENT_CONTENT]
        type_code = row[COL_ACCIDENT_TYPE]
        accident_type = ACCIDENT_TYPE_MAP.get(type_code) or ACCIDENT_CONTENT_MAP.get(
            content_code, "その他"
        )
    except (IndexError, ValueError):
        return None

    return {
        "year": year,
        "latitude": latitude,
        "longitude": longitude,
        "death_count": death_count,
        "injury_count": injury_count,
        "accident_type": accident_type,
    }


def in_bbox(lat: float, lng: float, bbox: tuple[float, float, float, float]) -> bool:
    min_lat, max_lat, min_lng, max_lng = bbox
    return min_lat <= lat <= max_lat and min_lng <= lng <= max_lng


def process_files(
    input_paths: list[Path], bbox: tuple[float, float, float, float]
) -> list[dict]:
    results: list[dict] = []
    for input_path in input_paths:
        if not input_path.exists():
            print(f"[warn] 入力ファイルが見つかりません: {input_path}", file=sys.stderr)
            continue
        with input_path.open(encoding="cp932", errors="replace", newline="") as f:
            reader = csv.reader(f)
            next(reader, None)  # ヘッダー行をスキップ
            for row in reader:
                converted = convert_row(row)
                if converted is None:
                    continue
                if in_bbox(converted["latitude"], converted["longitude"], bbox):
                    results.append(converted)
    return results


def generate_sample_data(count: int, bbox: tuple[float, float, float, float]) -> list[dict]:
    """実データが取得できない場合の現実的なサンプルデータ生成。

    仮定: サンプルデータ（実際の警察庁統計値ではない）。長崎市中心部近辺に
    偏らせつつbbox全体にランダム分布させ、事故種別・死傷者数もそれらしい分布にする。
    """
    rng = random.Random(42)
    accident_types = ["人対車両", "車両相互", "車両単独", "その他"]
    type_weights = [0.25, 0.55, 0.15, 0.05]

    # 長崎市中心部付近に密集させるための中心点
    center_lat, center_lng = 32.7503, 129.8777

    results = []
    for _ in range(count):
        if rng.random() < 0.6:
            # 6割は市街地中心付近（半径約0.05度=5km程度）に集中
            lat = center_lat + rng.uniform(-0.05, 0.05)
            lng = center_lng + rng.uniform(-0.05, 0.05)
        else:
            min_lat, max_lat, min_lng, max_lng = bbox
            lat = rng.uniform(min_lat, max_lat)
            lng = rng.uniform(min_lng, max_lng)

        accident_type = rng.choices(accident_types, weights=type_weights, k=1)[0]
        death = 1 if rng.random() < 0.02 else 0
        injury = 0 if death and rng.random() < 0.3 else rng.randint(1, 3)

        results.append(
            {
                "year": rng.choice([2021, 2022, 2023]),
                "latitude": round(lat, 6),
                "longitude": round(lng, 6),
                "death_count": death,
                "injury_count": injury,
                "accident_type": accident_type,
            }
        )
    return results


def write_output(rows: list[dict], output_path: Path, is_sample: bool) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        if is_sample:
            f.write(
                "# 仮定: サンプルデータ（警察庁オープンデータのDLに失敗したため生成した"
                "疑似データ。実際の事故統計値ではありません）\n"
            )
        writer = csv.writer(f)
        writer.writerow(
            ["year", "latitude", "longitude", "death_count", "injury_count", "accident_type"]
        )
        for row in rows:
            writer.writerow(
                [
                    row["year"],
                    row["latitude"],
                    row["longitude"],
                    row["death_count"],
                    row["injury_count"],
                    row["accident_type"],
                ]
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        nargs="*",
        type=Path,
        default=[DEFAULT_RAW],
        help="警察庁 honhyo CSV（CP932）のパス（複数年指定可）",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--bbox",
        nargs=4,
        type=float,
        default=DEFAULT_BBOX,
        metavar=("MIN_LAT", "MAX_LAT", "MIN_LNG", "MAX_LNG"),
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="実データを使わず現実的なサンプルデータを生成する",
    )
    parser.add_argument("--sample-count", type=int, default=3000)
    args = parser.parse_args()

    bbox = tuple(args.bbox)

    if args.sample:
        rows = generate_sample_data(args.sample_count, bbox)
        write_output(rows, args.output, is_sample=True)
        print(f"[sample] {len(rows)} 件のサンプルデータを {args.output} に出力しました")
        return

    rows = process_files(args.input, bbox)
    if not rows:
        print(
            "[warn] 実データから1件も抽出できませんでした。--sample での生成を検討してください",
            file=sys.stderr,
        )
        sys.exit(1)

    write_output(rows, args.output, is_sample=False)
    print(f"[real] {len(rows)} 件を {args.output} に出力しました（入力: {args.input}）")


if __name__ == "__main__":
    main()
