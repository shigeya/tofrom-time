"""検索条件を表す不変データ。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time
from enum import Enum


class TimeBasis(Enum):
    """時刻指定の種別（Yahoo の ``type`` パラメータに対応）。"""

    DEPART = "depart"  # 出発時刻指定 (type=1)
    ARRIVE = "arrive"  # 到着時刻指定 (type=4)


@dataclass(frozen=True)
class Query:
    """1 回の経路検索の条件。"""

    origin: str        # 出発駅（正式駅名）
    destination: str   # 到着駅（正式駅名）
    on: date           # 対象日
    at: time           # 指定時刻
    basis: TimeBasis   # 出発 or 到着
    use_limited_express: bool = False  # 有料特急（スカイライナー/NEX 等）を使う（ex=1）

    def __post_init__(self) -> None:
        if not self.origin:
            raise ValueError("origin（出発駅）が空です")
        if not self.destination:
            raise ValueError("destination（到着駅）が空です")
