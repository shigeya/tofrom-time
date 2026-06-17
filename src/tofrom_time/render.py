"""Route を人間向けテキストに整形する。"""

from __future__ import annotations

from .models import Route, Stop


def _stop_time(stop: Stop) -> str:
    """駅に表示する時刻。

    始発駅は出発時刻、終着駅は到着時刻、乗換駅は出発時刻（その駅を発つ時刻）。
    """
    return stop.depart or stop.arrive or ""


def render_oneline(route: Route) -> str:
    """乗換駅と発着駅を矢印でつないだ 1 行テキストを返す。

    例: ``分倍河原(13:26)→新宿(13:36)→成田空港(14:43)``
    """
    return "→".join(f"{s.name}({_stop_time(s)})" for s in route.stops)
