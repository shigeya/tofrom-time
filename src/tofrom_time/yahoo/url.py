"""Query から Yahoo!乗換案内 の検索 URL を組み立てる。"""

from __future__ import annotations

from urllib.parse import urlencode

from ..query import Query, TimeBasis

SEARCH_ENDPOINT = "https://transit.yahoo.co.jp/search/result"

# TimeBasis → Yahoo の type パラメータ（実機調査で確認済み）
_TYPE = {
    TimeBasis.DEPART: "1",
    TimeBasis.ARRIVE: "4",
}


def build_search_url(query: Query) -> str:
    """検索条件を URL に変換する。"""
    params = {
        "from": query.origin,
        "to": query.destination,
        "y": f"{query.on.year:04d}",
        "m": f"{query.on.month:02d}",
        "d": f"{query.on.day:02d}",
        "hh": f"{query.at.hour:02d}",
        "m1": str(query.at.minute // 10),  # 分の十の位
        "m2": str(query.at.minute % 10),   # 分の一の位
        "type": _TYPE[query.basis],
    }
    if query.use_limited_express:
        params["ex"] = "1"  # 有料特急を候補に含める
    return f"{SEARCH_ENDPOINT}?{urlencode(params)}"
