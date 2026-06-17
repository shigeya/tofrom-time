"""1行テキスト整形のテスト。"""

from tofrom_time.models import Leg, Route, Stop
from tofrom_time.render import render_oneline


def _route() -> Route:
    stops = (
        Stop("分倍河原", None, "13:26"),
        Stop("新宿", "13:33", "13:36"),
        Stop("成田空港", "14:43", None),
    )
    legs = (
        Leg(is_walk=False, line="京王線", direction="新宿行"),
        Leg(is_walk=False, line="JR", direction="成田空港行"),
    )
    return Route(
        stops=stops,
        legs=legs,
        depart_time="13:26",
        arrive_time="14:43",
        duration="1時間17分",
    )


def test_乗換駅と発着を矢印でつなぐ() -> None:
    text = render_oneline(_route())
    assert text == "分倍河原(13:26)→新宿(13:36)→成田空港(14:43)"


def test_始発は発時刻_終着は着時刻を使う() -> None:
    route = _route()
    text = render_oneline(route)
    # 始発は depart、終着は arrive を表示
    assert text.startswith("分倍河原(13:26)")
    assert text.endswith("成田空港(14:43)")


def test_実フィクスチャのルート1を整形できる(depart_html: str) -> None:
    from tofrom_time.yahoo.parser import parse_routes

    route = parse_routes(depart_html)[0]
    text = render_oneline(route)
    assert text.startswith("分倍河原(13:26)→")
    assert text.endswith("→成田空港(東京)(15:37)")
    assert text.count("→") == 6  # 7駅
