"""経路を表す不変データモデル。

すべて ``frozen=True`` の dataclass。生成後に状態を破壊的に変更しない。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Stop:
    """経路上の 1 駅（ノード）。

    - 始発駅は ``arrive`` が ``None``（出発のみ）。
    - 終着駅は ``depart`` が ``None``（到着のみ）。
    - 中間の乗換駅は両方を持つ。
    """

    name: str
    arrive: str | None  # "HH:MM" / 始発駅では None
    depart: str | None  # "HH:MM" / 終着駅では None


@dataclass(frozen=True)
class Leg:
    """隣り合う 2 駅の間の移動（乗車区間または徒歩）。"""

    is_walk: bool
    line: str | None = None       # 路線名（徒歩のときは None）
    direction: str | None = None  # 行き先方向（例: "新宿行"）


@dataclass(frozen=True)
class Route:
    """1 つの経路候補。

    ``stops`` は順序付きの駅列、``legs`` は駅間の移動列で
    ``len(legs) == len(stops) - 1`` を満たす。
    """

    stops: tuple[Stop, ...]
    legs: tuple[Leg, ...]
    depart_time: str            # 全体の出発時刻 "HH:MM"
    arrive_time: str            # 全体の到着時刻 "HH:MM"
    duration: str               # 所要時間の表示（例: "2時間11分"）
    fare: str | None = None     # 運賃の表示（例: "1,342円"）
    transfers: int | None = None
    labels: tuple[str, ...] = ()  # 早/安/楽 などの優先ラベル
    detail_url: str | None = None  # このルートの印刷用ページ URL（PDF 化に使う）

    def __post_init__(self) -> None:
        if len(self.legs) != len(self.stops) - 1:
            raise ValueError(
                f"legs={len(self.legs)} は stops={len(self.stops)} と整合しません"
                " (legs は stops-1 である必要があります)"
            )
