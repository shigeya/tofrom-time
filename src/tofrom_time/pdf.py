"""選択したルートの印刷用ページを PDF として保存する。

実ページのレンダリングは Playwright（ヘッドレス Chromium）で行う。
ブラウザ本体は別途 ``uv run playwright install chromium`` が必要。
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .models import Route
from .query import Query, TimeBasis

# (url, out_path) を受け取り PDF を書き出すレンダラ。テスト時は差し替え可能。
Renderer = Callable[[str, Path], None]


def pdf_filename(query: Query) -> str:
    """精算証憑向けの分かりやすいファイル名を生成する。

    例: ``2026-06-20_分倍河原-成田空港_1443着.pdf``
    """
    hhmm = f"{query.at.hour:02d}{query.at.minute:02d}"
    suffix = "着" if query.basis is TimeBasis.ARRIVE else "発"
    return (
        f"{query.on.isoformat()}_{query.origin}-{query.destination}_{hhmm}{suffix}.pdf"
    )


def save_route_pdf(
    route: Route,
    out_path: Path | str,
    *,
    render: Renderer | None = None,
) -> Path:
    """ルートの印刷用ページを PDF として ``out_path`` に保存する。"""
    if not route.detail_url:
        raise ValueError("このルートには印刷用 URL がありません（detail_url が None）")

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    renderer = render or _render_with_playwright
    renderer(route.detail_url, out)
    return out


def _render_with_playwright(url: str, out_path: Path) -> None:
    """Playwright で URL を開き PDF 化する（実ブラウザを起動）。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - 依存未導入時のみ
        raise RuntimeError(
            "playwright が見つかりません。`uv sync` 後に "
            "`uv run playwright install chromium` を実行してください。"
        ) from exc

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(url, wait_until="networkidle")
            page.pdf(path=str(out_path), format="A4", print_background=True)
        finally:
            browser.close()
