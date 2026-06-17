"""駅プリセット・ルールの読み込みと、設定ファイルの探索。

設定ファイル（stations.toml）の探索順:

1. 明示指定（``--config PATH`` / 各 load 関数の ``path`` 引数）
2. 環境変数 ``TOFROM_STATIONS``
3. カレントディレクトリの ``./config/stations.toml``（リポジトリ作業時）
4. ``~/.config/tofrom-time/stations.toml``（個人の既定。``XDG_CONFIG_HOME`` を尊重）
5. パッケージ同梱のデフォルト（最低限の別名・ルール）

最初に見つかったものを使う。
"""

from __future__ import annotations

import os
import shutil
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .preference import Preference, Rules

ENV_VAR = "TOFROM_STATIONS"

# パッケージ同梱のデフォルト（src/tofrom_time/data/stations.toml）。
# __file__ 基準なので editable でも wheel 導入でも解決できる。
PACKAGED_DEFAULT_PATH = Path(__file__).resolve().parent / "data" / "stations.toml"


def _xdg_config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))


def user_config_path() -> Path:
    """個人設定の標準パス（``~/.config/tofrom-time/stations.toml``）。"""
    return _xdg_config_home() / "tofrom-time" / "stations.toml"


def candidate_config_paths() -> list[Path]:
    """明示指定を除く探索候補を、優先順に返す。"""
    candidates: list[Path] = []
    env = os.environ.get(ENV_VAR)
    if env:
        candidates.append(Path(env).expanduser())
    candidates.append(Path.cwd() / "config" / "stations.toml")
    candidates.append(user_config_path())
    candidates.append(PACKAGED_DEFAULT_PATH)
    return candidates


def resolve_config_path(explicit: Path | str | None = None) -> Path | None:
    """実際に使う設定ファイルのパスを決める。

    ``explicit`` が指定された場合はそれだけを見る（存在しなければ None）。
    未指定なら探索チェーンの最初に存在するものを返す。
    """
    if explicit is not None:
        path = Path(explicit).expanduser()
        return path if path.exists() else None
    for candidate in candidate_config_paths():
        if candidate.exists():
            return candidate
    return None


def init_user_config(*, force: bool = False) -> Path:
    """同梱デフォルトを個人設定パスへコピーして、そのパスを返す。

    既に存在し ``force`` が False なら FileExistsError。
    """
    target = user_config_path()
    if target.exists() and not force:
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(PACKAGED_DEFAULT_PATH, target)
    return target


def _read_config(path: Path | str | None) -> dict | None:
    target = resolve_config_path(path)
    if target is None:
        return None
    with target.open("rb") as f:
        return tomllib.load(f)


@dataclass(frozen=True)
class Stations:
    """駅プリセット。別名→正式駅名のマップと、定番の出発・到着駅。"""

    aliases: dict[str, str] = field(default_factory=dict)
    origins: tuple[str, ...] = ()
    destinations: tuple[str, ...] = ()

    def resolve(self, name: str) -> str:
        """入力された駅名/別名を正式駅名に変換する。

        別名（大文字小文字を無視）に一致すれば対応する正式名を、
        一致しなければ入力をそのまま返す。
        """
        key = name.strip()
        return self.aliases.get(key.lower(), key)


def load_stations(path: Path | str | None = None) -> Stations:
    """設定を読み込み駅プリセットを返す。見つからなければ空の Stations。"""
    data = _read_config(path)
    if data is None:
        return Stations()

    raw_aliases = data.get("aliases", {})
    aliases = {str(k).lower(): str(v) for k, v in raw_aliases.items()}
    presets = data.get("presets", {})
    return Stations(
        aliases=aliases,
        origins=tuple(presets.get("origins", [])),
        destinations=tuple(presets.get("destinations", [])),
    )


def _build_preference(name: str, body: dict) -> Preference:
    return Preference(
        name=name,
        any_lines=tuple(body.get("any_lines", [])),
        via=tuple(body.get("via", [])),
        deny_lines=tuple(body.get("deny_lines", [])),
        prefer_lines=tuple(body.get("prefer_lines", [])),
        use_limited_express=bool(body.get("use_limited_express", False)),
    )


def load_rules(path: Path | str | None = None) -> Rules:
    """設定の [defaults] と [preferences.*] を読み込む。

    - ``[defaults]`` … 全検索に効く既定ルール（任意）
    - ``[preferences.<行き先>]`` … 行き先別ルール（行き先名がキー）
    """
    data = _read_config(path)
    if data is None:
        return Rules()

    default = None
    if "defaults" in data:
        default = _build_preference("default", data["defaults"])

    by_destination = {
        name: _build_preference(name, body)
        for name, body in data.get("preferences", {}).items()
    }
    return Rules(default=default, by_destination=by_destination)
