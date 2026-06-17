"""Yahoo!乗換案内 検索結果 HTML → Route 構造化。

実機調査済みの DOM（2026-06 時点）に対応する。HTML 構造が変わると壊れる
前提で、抽出ロジックはここに閉じ込めておく（取得・URL 構築とは分離）。
"""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from ..models import Leg, Route, Stop

_BASE = "https://transit.yahoo.co.jp"

_TIME = re.compile(r"(\d{1,2}:\d{2})")
_DURATION = re.compile(r"着\s*((?:\d+時間)?\d+分)")
_FARE = re.compile(r"([\d,]+)\s*円")
_TRANSFERS = re.compile(r"乗換[：:]*\s*(\d+)\s*回")


def parse_routes(html: str) -> tuple[Route, ...]:
    """検索結果ページの HTML から候補ルート列を返す。"""
    soup = BeautifulSoup(html, "lxml")
    routes: list[Route] = []
    for detail in soup.select("div.routeDetail"):
        container = detail.parent
        summary = container.select_one("div.routeSummary") if container else None
        routes.append(_parse_route(detail, summary, container))
    return tuple(routes)


def _parse_detail_url(container: Tag | None) -> str | None:
    if container is None:
        return None
    link = container.select_one('a[href*="/search/print"]')
    href = link.get("href") if link else None
    return urljoin(_BASE, href) if href else None


def _parse_route(detail: Tag, summary: Tag | None, container: Tag | None) -> Route:
    stops = tuple(_parse_stop(s) for s in detail.select("div.station"))
    legs = tuple(_parse_leg(li) for li in detail.select("li.transport"))
    depart, arrive, duration = _parse_summary_time(summary)
    return Route(
        stops=stops,
        legs=legs,
        depart_time=depart,
        arrive_time=arrive,
        duration=duration,
        fare=_parse_fare(summary),
        transfers=_parse_transfers(summary),
        labels=_parse_labels(summary),
        detail_url=_parse_detail_url(container),
    )


def _parse_stop(station: Tag) -> Stop:
    name_el = station.select_one("dl dt")
    name = name_el.get_text(strip=True) if name_el else ""

    icons = {c for span in station.select("p.icon span") for c in (span.get("class") or [])}

    arrive: str | None = None
    depart: str | None = None
    for li in station.select("ul.time li"):
        raw = li.get_text(strip=True)
        m = _TIME.search(raw)
        if not m:
            continue
        value = m.group(1)
        if "着" in raw:
            arrive = value
        elif "発" in raw:
            depart = value
        elif "icnStaArr" in icons:  # マーカーなし＝終着（到着のみ）
            arrive = value
        else:  # マーカーなし＝始発（出発のみ）
            depart = value
    return Stop(name=name, arrive=arrive, depart=depart)


def _parse_leg(transport: Tag) -> Leg:
    text = re.sub(r"\s+", " ", transport.get_text(" ", strip=True)).strip()
    if text == "徒歩":
        return Leg(is_walk=True)

    dest_el = transport.select_one("span.destination")
    direction = dest_el.get_text(strip=True) if dest_el else None
    if direction and text.endswith(direction):
        line = text[: -len(direction)].strip()
    else:
        line = text
    return Leg(is_walk=False, line=line or None, direction=direction)


def _parse_summary_time(summary: Tag | None) -> tuple[str, str, str]:
    if summary is None:
        return "", "", ""
    time_el = summary.select_one("li.time")
    text = time_el.get_text(" ", strip=True) if time_el else ""
    times = _TIME.findall(text)
    depart = times[0] if times else ""
    arrive = times[1] if len(times) > 1 else ""
    dm = _DURATION.search(text)
    duration = dm.group(1) if dm else ""
    return depart, arrive, duration


def _parse_fare(summary: Tag | None) -> str | None:
    if summary is None:
        return None
    fare_el = summary.select_one(".fare")
    if fare_el is None:
        return None
    m = _FARE.search(fare_el.get_text(" ", strip=True))
    return f"{m.group(1)}円" if m else None


def _parse_transfers(summary: Tag | None) -> int | None:
    if summary is None:
        return None
    m = _TRANSFERS.search(summary.get_text(" ", strip=True))
    return int(m.group(1)) if m else None


def _parse_labels(summary: Tag | None) -> tuple[str, ...]:
    if summary is None:
        return ()
    return tuple(
        li.get_text(strip=True)
        for li in summary.select(".priority li")
        if li.get_text(strip=True)
    )
