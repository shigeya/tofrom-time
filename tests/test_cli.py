"""CLI のテスト（ネットワークはフェイククライアントで置き換える）。"""

import json

import pytest
import typer
from typer.testing import CliRunner

from tofrom_time import cli
from tofrom_time.config import Stations
from tofrom_time.query import TimeBasis

runner = CliRunner()


# --- build_query の検証 -------------------------------------------------

def _stations() -> Stations:
    return Stations(aliases={"narita": "成田空港"})


def test_depart指定でDEPARTのQueryになる() -> None:
    q = cli.build_query(
        origin="分倍河原", destination="narita",
        depart="13:19", arrive=None, on="2026-06-20", stations=_stations(),
    )
    assert q.basis is TimeBasis.DEPART
    assert q.destination == "成田空港"  # 別名解決
    assert (q.at.hour, q.at.minute) == (13, 19)


def test_arrive指定でARRIVEのQueryになる() -> None:
    q = cli.build_query(
        origin="分倍河原", destination="成田空港",
        depart=None, arrive="14:43", on=None, stations=_stations(),
    )
    assert q.basis is TimeBasis.ARRIVE


def test_departとarrive両方はエラー() -> None:
    with pytest.raises(typer.BadParameter):
        cli.build_query(
            origin="A", destination="B",
            depart="10:00", arrive="11:00", on=None, stations=_stations(),
        )


def test_どちらも無指定はエラー() -> None:
    with pytest.raises(typer.BadParameter):
        cli.build_query(
            origin="A", destination="B",
            depart=None, arrive=None, on=None, stations=_stations(),
        )


# --- コマンド全体 -------------------------------------------------------

class _FakeClient:
    """fetch_result が固定 HTML を返すフェイク。"""

    html = ""

    def __init__(self, *args, **kwargs) -> None:
        pass

    def __enter__(self) -> "_FakeClient":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def fetch_result(self, query) -> str:
        return _FakeClient.html


@pytest.fixture(autouse=True)
def _patch_client(monkeypatch, depart_html: str):
    _FakeClient.html = depart_html
    monkeypatch.setattr(cli, "YahooClient", _FakeClient)


def test_pick指定で選択ルートを1行出力() -> None:
    result = runner.invoke(
        cli.app,
        ["--from", "分倍河原", "--to", "成田空港", "--depart", "13:19", "--pick", "1"],
    )
    assert result.exit_code == 0
    assert "分倍河原(13:26)" in result.stdout
    assert "→成田空港(東京)(15:37)" in result.stdout


def test_json出力は全候補を含む() -> None:
    result = runner.invoke(
        cli.app,
        ["--from", "分倍河原", "--to", "成田空港", "--arrive", "14:43", "--json"],
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert len(data) == 3
    assert data[0]["oneline"].startswith("分倍河原(")


def test_pick範囲外はエラー() -> None:
    result = runner.invoke(
        cli.app,
        ["--from", "分倍河原", "--to", "成田空港", "--depart", "13:19", "--pick", "9"],
    )
    assert result.exit_code != 0


# --- resolve_preference ----------------------------------------------------

def _rules() -> cli.Rules:
    return cli.Rules(
        default=None,
        by_destination={
            "成田空港": cli.Preference(
                name="成田空港",
                any_lines=("スカイライナー", "成田エクスプレス"),
                use_limited_express=True,
            ),
        },
    )


def test_行き先で条件が自動適用される() -> None:
    pref = cli.resolve_preference(
        prefer=None, show_all=False, destination="成田空港", rules=_rules()
    )
    assert pref is not None and pref.name == "成田空港"


def test_allなら条件を無視する() -> None:
    pref = cli.resolve_preference(
        prefer=None, show_all=True, destination="成田空港", rules=_rules()
    )
    assert pref is None


def test_未知のprefer名はエラー() -> None:
    with pytest.raises(typer.BadParameter):
        cli.resolve_preference(
            prefer="未定義", show_all=False, destination="成田空港", rules=_rules()
        )


# --- 設定ファイル関連フラグ -------------------------------------------------

def test_fromとtoが無ければエラー() -> None:
    result = runner.invoke(cli.app, [])
    assert result.exit_code != 0


def test_show_configは探索結果を表示して終了() -> None:
    result = runner.invoke(cli.app, ["--show-config"])
    assert result.exit_code == 0
    assert "使用される設定" in result.stdout


def test_存在しないconfig指定はエラー() -> None:
    result = runner.invoke(
        cli.app,
        ["--from", "分倍河原", "--to", "成田空港", "--depart", "13:19",
         "--config", "/no/such/file.toml"],
    )
    assert result.exit_code != 0


def test_条件に合う候補が無ければ全件にフォールバック() -> None:
    # フィクスチャ(ex 無)はスカイライナー等を含まない → フォールバック
    result = runner.invoke(
        cli.app,
        ["--from", "分倍河原", "--to", "成田空港", "--depart", "13:19", "--json"],
    )
    assert result.exit_code == 0
    # 全 3 件が出る（絞り込みでゼロにはしない）
    assert len(json.loads(result.stdout)) == 3
