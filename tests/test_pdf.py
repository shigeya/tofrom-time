"""PDF 保存ロジックのテスト（実ブラウザは起動しない）。"""

from datetime import date, time
from pathlib import Path

import pytest

from tofrom_time.models import Leg, Route, Stop
from tofrom_time.pdf import pdf_filename, save_route_pdf
from tofrom_time.query import Query, TimeBasis


def _route(detail_url: str | None) -> Route:
    return Route(
        stops=(Stop("A", None, "10:00"), Stop("B", "10:30", None)),
        legs=(Leg(is_walk=False, line="X線", direction="B行"),),
        depart_time="10:00",
        arrive_time="10:30",
        duration="30分",
        detail_url=detail_url,
    )


def test_ファイル名は日付_区間_時刻で作る() -> None:
    q = Query(
        origin="分倍河原", destination="成田空港",
        on=date(2026, 6, 20), at=time(14, 43), basis=TimeBasis.ARRIVE,
    )
    assert pdf_filename(q) == "2026-06-20_分倍河原-成田空港_1443着.pdf"


def test_出発指定は発サフィックス() -> None:
    q = Query(
        origin="溝の口", destination="羽田空港",
        on=date(2026, 1, 5), at=time(9, 4), basis=TimeBasis.DEPART,
    )
    assert pdf_filename(q) == "2026-01-05_溝の口-羽田空港_0904発.pdf"


def test_detail_urlをレンダラに渡して保存する(tmp_path: Path) -> None:
    seen: dict[str, object] = {}

    def fake_render(url: str, out_path: Path) -> None:
        seen["url"] = url
        out_path.write_bytes(b"%PDF-1.4 fake")

    out = tmp_path / "route.pdf"
    result = save_route_pdf(
        _route("https://transit.yahoo.co.jp/search/print?no=1"),
        out,
        render=fake_render,
    )
    assert result == out
    assert out.read_bytes().startswith(b"%PDF")
    assert seen["url"] == "https://transit.yahoo.co.jp/search/print?no=1"


def test_detail_urlが無ければエラー(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        save_route_pdf(_route(None), tmp_path / "x.pdf", render=lambda u, p: None)
