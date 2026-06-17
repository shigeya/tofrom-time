"""駅プリセット読み込み・別名解決のテスト。"""

from pathlib import Path

import pytest

from tofrom_time.config import (
    ENV_VAR,
    PACKAGED_DEFAULT_PATH,
    Stations,
    candidate_config_paths,
    init_user_config,
    load_rules,
    load_stations,
    resolve_config_path,
    user_config_path,
)


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


# --- 設定ファイルの探索チェーン ----------------------------------------------

_SAMPLE = """
[aliases]
foo = "テスト駅"
"""


def test_明示パスが最優先で読まれる(tmp_path: Path) -> None:
    cfg = tmp_path / "custom.toml"
    cfg.write_text(_SAMPLE, encoding="utf-8")
    stations = load_stations(cfg)
    assert stations.resolve("foo") == "テスト駅"


def test_環境変数で設定を切り替えられる(tmp_path, monkeypatch) -> None:
    cfg = tmp_path / "env.toml"
    cfg.write_text(_SAMPLE, encoding="utf-8")
    monkeypatch.setenv(ENV_VAR, str(cfg))
    assert resolve_config_path() == cfg
    assert load_stations().resolve("foo") == "テスト駅"


def test_どこにも無ければ同梱デフォルトにフォールバックする(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv(ENV_VAR, raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))  # 空ディレクトリ
    monkeypatch.chdir(tmp_path)  # ./config を無くす
    assert resolve_config_path() == PACKAGED_DEFAULT_PATH


def test_init_user_configは同梱デフォルトを個人パスへ複製(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    created = init_user_config()
    assert created == user_config_path()
    assert created.read_text(encoding="utf-8") == PACKAGED_DEFAULT_PATH.read_text(
        encoding="utf-8"
    )
    # 既存時は上書きしない
    with pytest.raises(FileExistsError):
        init_user_config()


def test_candidate_config_pathsは優先順を返す(monkeypatch) -> None:
    monkeypatch.delenv(ENV_VAR, raising=False)
    paths = candidate_config_paths()
    assert paths[-1] == PACKAGED_DEFAULT_PATH  # 最後は同梱デフォルト
