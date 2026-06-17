"""検索 URL 構築のテスト。"""

from datetime import date, time
from urllib.parse import parse_qs, urlparse

from tofrom_time.query import Query, TimeBasis
from tofrom_time.yahoo.url import SEARCH_ENDPOINT, build_search_url


def _query(basis: TimeBasis) -> Query:
    return Query(
        origin="分倍河原",
        destination="成田空港",
        on=date(2026, 6, 20),
        at=time(13, 19),
        basis=basis,
    )


def test_出発時刻指定のURLパラメータ() -> None:
    url = build_search_url(_query(TimeBasis.DEPART))
    parsed = urlparse(url)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == SEARCH_ENDPOINT
    q = parse_qs(parsed.query)
    assert q["from"] == ["分倍河原"]
    assert q["to"] == ["成田空港"]
    assert q["y"] == ["2026"]
    assert q["m"] == ["06"]
    assert q["d"] == ["20"]
    assert q["hh"] == ["13"]
    assert q["m1"] == ["1"]  # 19分 → 十の位 1
    assert q["m2"] == ["9"]  # 19分 → 一の位 9
    assert q["type"] == ["1"]


def test_到着時刻指定はtype4() -> None:
    url = build_search_url(_query(TimeBasis.ARRIVE))
    q = parse_qs(urlparse(url).query)
    assert q["type"] == ["4"]


def test_分が0埋め桁で正しく分解される() -> None:
    query = Query(
        origin="溝の口",
        destination="羽田空港",
        on=date(2026, 1, 5),
        at=time(9, 4),
        basis=TimeBasis.DEPART,
    )
    q = parse_qs(urlparse(build_search_url(query)).query)
    assert q["m"] == ["01"]
    assert q["d"] == ["05"]
    assert q["hh"] == ["09"]
    assert q["m1"] == ["0"]
    assert q["m2"] == ["4"]
