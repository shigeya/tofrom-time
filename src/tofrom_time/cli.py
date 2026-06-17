"""旅費精算用 経路表示 CLI のエントリポイント。"""

from __future__ import annotations

import json
from datetime import date, datetime, time
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .config import Stations, load_rules, load_stations
from .models import Route
from .pdf import pdf_filename, save_route_pdf
from .preference import Preference, Rules, filter_routes
from .query import Query, TimeBasis
from .render import render_oneline
from .yahoo.client import YahooClient
from .yahoo.parser import parse_routes

app = typer.Typer(add_completion=False, help="旅費精算用の経路表示 CLI（Yahoo!乗換案内）")
console = Console()

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "tofrom-time"


def _parse_hhmm(value: str) -> time:
    try:
        hh, mm = value.split(":")
        return time(int(hh), int(mm))
    except (ValueError, AttributeError) as exc:
        raise typer.BadParameter(f"時刻は HH:MM 形式で指定してください: {value!r}") from exc


def _parse_date(value: str | None) -> date:
    if value is None:
        return datetime.now().date()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise typer.BadParameter(f"日付は YYYY-MM-DD 形式で指定してください: {value!r}") from exc


def build_query(
    *,
    origin: str,
    destination: str,
    depart: str | None,
    arrive: str | None,
    on: str | None,
    stations: Stations,
    use_limited_express: bool = False,
) -> Query:
    """CLI 引数を検証して Query を作る。

    ``depart`` と ``arrive`` はどちらか一方のみ指定可能。
    """
    if depart and arrive:
        raise typer.BadParameter("--depart と --arrive は同時に指定できません")
    if not depart and not arrive:
        raise typer.BadParameter("--depart または --arrive のいずれかを指定してください")

    if depart:
        at, basis = _parse_hhmm(depart), TimeBasis.DEPART
    else:
        at, basis = _parse_hhmm(arrive), TimeBasis.ARRIVE

    return Query(
        origin=stations.resolve(origin),
        destination=stations.resolve(destination),
        on=_parse_date(on),
        at=at,
        basis=basis,
        use_limited_express=use_limited_express,
    )


def resolve_preference(
    *,
    prefer: str | None,
    show_all: bool,
    destination: str,
    rules: Rules,
) -> Preference | None:
    """適用するルート選択条件を決める（既定ルールも考慮）。

    優先順位: ``--all`` 指定 > ``--prefer NAME`` 指定 > 行き先による自動適用。
    """
    try:
        return rules.resolve(
            prefer=prefer, show_all=show_all, destination=destination
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


def _render_candidates_table(routes: tuple[Route, ...]) -> Table:
    table = Table(title="候補ルート")
    table.add_column("#", justify="right")
    table.add_column("出発")
    table.add_column("到着")
    table.add_column("所要")
    table.add_column("乗換", justify="right")
    table.add_column("運賃", justify="right")
    table.add_column("特徴")
    for i, r in enumerate(routes, 1):
        table.add_row(
            str(i),
            r.depart_time,
            r.arrive_time,
            r.duration,
            "" if r.transfers is None else f"{r.transfers}回",
            r.fare or "",
            "".join(r.labels),
        )
    return table


def _route_to_dict(route: Route) -> dict:
    return {
        "depart": route.depart_time,
        "arrive": route.arrive_time,
        "duration": route.duration,
        "transfers": route.transfers,
        "fare": route.fare,
        "labels": list(route.labels),
        "oneline": render_oneline(route),
        "stops": [
            {"name": s.name, "arrive": s.arrive, "depart": s.depart}
            for s in route.stops
        ],
    }


@app.command()
def main(
    origin: str = typer.Option(..., "--from", help="出発駅（別名可）"),
    destination: str = typer.Option(..., "--to", help="到着駅（別名可）"),
    depart: str | None = typer.Option(None, "--depart", help="出発時刻 HH:MM"),
    arrive: str | None = typer.Option(None, "--arrive", help="到着時刻 HH:MM"),
    on: str | None = typer.Option(None, "--date", help="日付 YYYY-MM-DD（既定: 当日）"),
    pick: int | None = typer.Option(None, "--pick", help="候補番号を指定（非対話）"),
    as_json: bool = typer.Option(False, "--json", help="JSON で出力"),
    no_cache: bool = typer.Option(False, "--no-cache", help="キャッシュを使わない"),
    pdf_dir: str | None = typer.Option(
        None, "--pdf", help="選択ルートの印刷ページを PDF 保存する出力先ディレクトリ"
    ),
    prefer: str | None = typer.Option(
        None, "--prefer", help="ルート選択条件を名前で指定（既定は行き先で自動）"
    ),
    show_all: bool = typer.Option(
        False, "--all", help="選択条件を無視して全候補を表示"
    ),
) -> None:
    """経路を検索し、選択ルートを 1 行テキストで出力する。"""
    stations = load_stations()
    rules = load_rules()
    destination_resolved = stations.resolve(destination)
    preference = resolve_preference(
        prefer=prefer,
        show_all=show_all,
        destination=destination_resolved,
        rules=rules,
    )

    query = build_query(
        origin=origin,
        destination=destination,
        depart=depart,
        arrive=arrive,
        on=on,
        stations=stations,
        use_limited_express=preference.use_limited_express if preference else False,
    )

    cache_dir = None if no_cache else DEFAULT_CACHE_DIR
    with YahooClient(cache_dir=cache_dir) as client:
        routes = parse_routes(client.fetch_result(query))

    if not routes:
        console.print("[red]経路が見つかりませんでした。[/red]")
        raise typer.Exit(code=1)

    routes = _apply_preference(routes, preference, quiet=as_json)

    if as_json:
        console.print_json(json.dumps([_route_to_dict(r) for r in routes], ensure_ascii=False))
        return

    selected = _select_route(routes, pick)
    console.print(render_oneline(selected))

    if pdf_dir is not None:
        out_path = Path(pdf_dir) / pdf_filename(query)
        try:
            saved = save_route_pdf(selected, out_path)
        except (RuntimeError, ValueError) as exc:
            console.print(f"[red]PDF 保存に失敗しました: {exc}[/red]")
            raise typer.Exit(code=1) from exc
        console.print(f"[green]PDF を保存しました:[/green] {saved}")


def _apply_preference(
    routes: tuple[Route, ...],
    preference: Preference | None,
    *,
    quiet: bool,
) -> tuple[Route, ...]:
    """選択条件で候補を絞り込む。

    条件に合うルートが 1 件も無ければ、警告して全候補を返す（取りこぼし防止）。
    """
    if preference is None:
        return routes
    matched = filter_routes(routes, preference)
    if not matched:
        if not quiet:
            console.print(
                f"[yellow]条件「{preference.name}」に合うルートが無いため"
                "全候補を表示します。[/yellow]"
            )
        return routes
    if not quiet and len(matched) < len(routes):
        console.print(
            f"[dim]条件「{preference.name}」で "
            f"{len(routes)}→{len(matched)} 件に絞り込みました。[/dim]"
        )
    return matched


def _select_route(routes: tuple[Route, ...], pick: int | None) -> Route:
    if pick is not None:
        if not 1 <= pick <= len(routes):
            raise typer.BadParameter(f"--pick は 1〜{len(routes)} で指定してください")
        return routes[pick - 1]

    if len(routes) == 1:
        return routes[0]

    console.print(_render_candidates_table(routes))
    choice = typer.prompt("ルート番号を選択", default=1, type=int)
    if not 1 <= choice <= len(routes):
        raise typer.BadParameter(f"番号は 1〜{len(routes)} で指定してください")
    return routes[choice - 1]


if __name__ == "__main__":
    app()
