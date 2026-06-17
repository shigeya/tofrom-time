"""Yahoo!乗換案内 検索結果 HTML のパーサのテスト。

ネットワークには依存せず、tests/fixtures/ に保存済みの実 HTML を対象にする。
"""

from tofrom_time.models import Route, Stop
from tofrom_time.yahoo.parser import parse_routes


def test_候補ルートが3件抽出される(depart_html: str) -> None:
    routes = parse_routes(depart_html)
    assert len(routes) == 3
    assert all(isinstance(r, Route) for r in routes)


def test_ルート1の全体サマリ(depart_html: str) -> None:
    route = parse_routes(depart_html)[0]
    assert route.depart_time == "13:26"
    assert route.arrive_time == "15:37"
    assert route.duration == "2時間11分"
    assert route.transfers == 3
    assert route.fare == "1,386円"
    assert route.labels == ("早", "安")


def test_ルート1の駅列_先頭は発のみ末尾は着のみ(depart_html: str) -> None:
    route = parse_routes(depart_html)[0]
    assert len(route.stops) == 7
    assert route.stops[0] == Stop(name="分倍河原", arrive=None, depart="13:26")
    assert route.stops[1] == Stop(name="笹塚", arrive="13:30", depart="13:32")
    assert route.stops[-1] == Stop(name="成田空港(東京)", arrive="15:37", depart=None)


def test_ルート1の区間_路線と徒歩(depart_html: str) -> None:
    route = parse_routes(depart_html)[0]
    assert len(route.legs) == 6
    # 最初の区間は京王線・新宿方面の乗車
    assert route.legs[0].is_walk is False
    assert route.legs[0].line == "京王線"
    assert route.legs[0].direction == "新宿行"
    # 3 区間目は徒歩
    assert route.legs[2].is_walk is True
    assert route.legs[2].line is None


def test_各ルートに印刷用URLが付く(depart_html: str) -> None:
    routes = parse_routes(depart_html)
    assert routes[0].detail_url is not None
    assert "/search/print" in routes[0].detail_url
    assert routes[0].detail_url.startswith("https://transit.yahoo.co.jp")
    # no パラメータがルート番号に対応する
    assert "no=1" in routes[0].detail_url
    assert "no=2" in routes[1].detail_url


def test_到着指定HTMLもパースできる(arrive_html: str) -> None:
    routes = parse_routes(arrive_html)
    assert len(routes) >= 1
    # 到着指定なので最良ルートは 14:43 までに着く
    first = routes[0]
    assert first.arrive_time <= "14:43"
