"""警察庁事故データ（`data/accidents.csv`）のグリッドインデックスと近傍検索。

起動時（初回アクセス時）に一度だけCSVを読み込み、0.001度四方のグリッドセルへ
事故地点を割り当てる。`count_near` はクエリ地点周辺の3x3セル（=約0.003度四方、
緯度35度付近で約330m四方）候補のみをhaversine距離で厳密フィルタすることで、
全件走査を避けつつ高速に近傍事故件数を求める。
"""

from __future__ import annotations

import csv
import logging
import threading
from dataclasses import dataclass
from pathlib import Path

from app.core.geo import haversine_distance_m

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
ACCIDENTS_FILE = DATA_DIR / "accidents.csv"

GRID_CELL_DEGREES = 0.001


@dataclass(frozen=True)
class AccidentPoint:
    year: str
    latitude: float
    longitude: float
    death_count: int
    injury_count: int
    accident_type: str


class AccidentGridIndex:
    def __init__(self) -> None:
        self._grid: dict[tuple[int, int], list[AccidentPoint]] = {}
        self._loaded = False
        self._count = 0

    def _cell_key(self, lat: float, lng: float) -> tuple[int, int]:
        return (int(lat // GRID_CELL_DEGREES), int(lng // GRID_CELL_DEGREES))

    def load(self, path: Path = ACCIDENTS_FILE) -> None:
        self._grid.clear()
        self._count = 0
        if not path.exists():
            logger.warning("事故データファイルが見つかりません: %s", path)
            self._loaded = True
            return

        with path.open(encoding="utf-8", newline="") as f:
            lines = (line for line in f if not line.lstrip().startswith("#"))
            reader = csv.DictReader(lines)
            for row in reader:
                try:
                    point = AccidentPoint(
                        year=row["year"],
                        latitude=float(row["latitude"]),
                        longitude=float(row["longitude"]),
                        death_count=int(row["death_count"]),
                        injury_count=int(row["injury_count"]),
                        accident_type=row["accident_type"],
                    )
                except (KeyError, ValueError):
                    continue
                key = self._cell_key(point.latitude, point.longitude)
                self._grid.setdefault(key, []).append(point)
                self._count += 1

        self._loaded = True
        logger.info("事故データ %d 件を %d セルへロードしました", self._count, len(self._grid))

    def ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    @property
    def count(self) -> int:
        self.ensure_loaded()
        return self._count

    def count_near(self, lat: float, lng: float, radius_m: float = 50) -> int:
        """指定地点からradius_m以内にある事故地点数を返す。"""
        return len(self.points_near(lat, lng, radius_m))

    def points_near(self, lat: float, lng: float, radius_m: float = 50) -> list[AccidentPoint]:
        self.ensure_loaded()
        center_key = self._cell_key(lat, lng)
        candidates: list[AccidentPoint] = []
        for d_lat in (-1, 0, 1):
            for d_lng in (-1, 0, 1):
                key = (center_key[0] + d_lat, center_key[1] + d_lng)
                candidates.extend(self._grid.get(key, []))

        return [
            point
            for point in candidates
            if haversine_distance_m(lat, lng, point.latitude, point.longitude) <= radius_m
        ]


_index_lock = threading.Lock()
_index: AccidentGridIndex | None = None


def get_index() -> AccidentGridIndex:
    global _index
    if _index is None:
        with _index_lock:
            if _index is None:
                _index = AccidentGridIndex()
                _index.ensure_loaded()
    return _index


def count_near(lat: float, lng: float, radius_m: float = 50) -> int:
    return get_index().count_near(lat, lng, radius_m)


def reset_index_for_tests(path: Path) -> AccidentGridIndex:
    """テスト用に別ファイル（tmp_path等）からインデックスを再構築する。"""
    global _index
    with _index_lock:
        _index = AccidentGridIndex()
        _index.load(path)
    return _index
