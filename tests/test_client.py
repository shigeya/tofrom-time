"""取得クライアントのテスト（httpx.MockTransport でネットワーク非依存）。"""

from datetime import date, time
from pathlib import Path

import httpx

from tofrom_time.query import Query, TimeBasis
from tofrom_time.yahoo.client import USER_AGENT, YahooClient


def _query() -> Query:
    return Query(
        origin="分倍河原",
        destination="成田空港",
        on=date(2026, 6, 20),
        at=time(13, 19),
        basis=TimeBasis.DEPART,
    )


def _client(handler, **kwargs) -> YahooClient:
    transport = httpx.MockTransport(handler)
    return YahooClient(transport=transport, min_interval=0.0, sleep=lambda _s: None, **kwargs)


def test_検索結果のHTMLを返す() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>OK</html>")

    with _client(handler) as client:
        assert client.fetch_result(_query()) == "<html>OK</html>"


def test_User_Agentを明示して送る() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["ua"] = request.headers.get("user-agent", "")
        return httpx.Response(200, text="ok")

    with _client(handler) as client:
        client.fetch_result(_query())
    assert seen["ua"] == USER_AGENT


def test_HTTPエラーは例外になる() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="busy")

    with _client(handler) as client:
        try:
            client.fetch_result(_query())
        except httpx.HTTPStatusError:
            pass
        else:  # pragma: no cover
            raise AssertionError("HTTPStatusError が送出されるべき")


def test_キャッシュ有効時は2回目はネットワークを叩かない(tmp_path: Path) -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, text="<html>cached</html>")

    with _client(handler, cache_dir=tmp_path) as client:
        first = client.fetch_result(_query())
        second = client.fetch_result(_query())

    assert first == second == "<html>cached</html>"
    assert calls["n"] == 1  # 2 回目はキャッシュから


def test_最小間隔を満たすためsleepする() -> None:
    waits: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="ok")

    clock = {"t": 0.0}
    transport = httpx.MockTransport(handler)
    client = YahooClient(
        transport=transport,
        min_interval=2.0,
        sleep=lambda s: waits.append(s),
        monotonic=lambda: clock["t"],
    )
    client.fetch_result(_query())  # 1 回目は待たない
    client.fetch_result(_query())  # 直後なので 2 秒待つ
    client.close()

    assert waits == [2.0]
