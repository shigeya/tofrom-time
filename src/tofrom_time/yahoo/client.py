"""Yahoo!乗換案内 からの取得クライアント。

個人利用・低頻度を前提に、UA 明示・リクエスト間隔・簡易キャッシュを備える。
URL 構築（url.py）と解析（parser.py）からは分離する。
"""

from __future__ import annotations

import hashlib
import time as _time
from collections.abc import Callable
from pathlib import Path

import httpx

from ..query import Query
from .url import build_search_url

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

DEFAULT_TIMEOUT = 20.0
DEFAULT_MIN_INTERVAL = 1.0  # 連続アクセスの最小間隔（秒）


class YahooClient:
    """検索結果ページを取得する。"""

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        transport: httpx.BaseTransport | None = None,
        min_interval: float = DEFAULT_MIN_INTERVAL,
        cache_dir: Path | str | None = None,
        sleep: Callable[[float], None] = _time.sleep,
        monotonic: Callable[[], float] = _time.monotonic,
    ) -> None:
        self._client = client or httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=DEFAULT_TIMEOUT,
            follow_redirects=True,
            transport=transport,
        )
        self._owns_client = client is None
        self._min_interval = min_interval
        self._cache_dir = Path(cache_dir) if cache_dir else None
        self._sleep = sleep
        self._monotonic = monotonic
        self._last_request_at: float | None = None

    def fetch_result(self, query: Query) -> str:
        """Query に対応する検索結果ページの HTML を返す。"""
        url = build_search_url(query)

        cached = self._read_cache(url)
        if cached is not None:
            return cached

        self._respect_interval()
        response = self._client.get(url)
        response.raise_for_status()
        html = response.text

        self._write_cache(url, html)
        return html

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> YahooClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # --- 内部処理 ---------------------------------------------------------

    def _respect_interval(self) -> None:
        if self._last_request_at is not None:
            elapsed = self._monotonic() - self._last_request_at
            wait = self._min_interval - elapsed
            if wait > 0:
                self._sleep(wait)
        self._last_request_at = self._monotonic()

    def _cache_path(self, url: str) -> Path | None:
        if self._cache_dir is None:
            return None
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self._cache_dir / f"{digest}.html"

    def _read_cache(self, url: str) -> str | None:
        path = self._cache_path(url)
        if path is not None and path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def _write_cache(self, url: str, html: str) -> None:
        path = self._cache_path(url)
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(html, encoding="utf-8")
