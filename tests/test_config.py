"""駅プリセット読み込み・別名解決のテスト。"""

from pathlib import Path

from tofrom_time.config import Stations, load_rules, load_stations


def test_既定のstations_tomlを読み込める() -> None:
    stations = load_stations()
    assert "分倍河原" in stations.origins
    assert "成田空港" in stations.destinations
    assert stations.resolve("narita") == "成田空港"


def test_別名は大文字小文字を無視して解決() -> None:
    stations = Stations(aliases={"narita": "成田空港"})
    assert stations.resolve("NARITA") == "成田空港"
    assert stations.resolve("Narita") == "成田空港"


def test_未知の駅名はそのまま返す() -> None:
    stations = Stations(aliases={"narita": "成田空港"})
    assert stations.resolve("分倍河原") == "分倍河原"


def test_存在しないパスは空のStations() -> None:
    stations = load_stations(Path("/no/such/stations.toml"))
    assert stations == Stations()
    assert stations.resolve("foo") == "foo"


def test_rulesを読み込める() -> None:
    rules = load_rules()
    narita = rules.by_destination["成田空港"]
    assert narita.use_limited_express is True
    assert "スカイライナー" in narita.any_lines
    assert "成田エクスプレス" in narita.any_lines
    haneda = rules.by_destination["羽田空港"]
    assert haneda.any_lines == ("京急",)
    assert haneda.deny_lines == ("京王線",)
    assert haneda.prefer_lines == ("田園都市線",)


def test_存在しないパスは空のRules() -> None:
    rules = load_rules(Path("/no/such/stations.toml"))
    assert rules.default is None
    assert rules.by_destination == {}
