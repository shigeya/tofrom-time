"""駅プリセット（config/stations.toml）の読み込みと別名解決。"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .preference import Preference, Rules

# プロジェクトルート直下の config/stations.toml を既定とする
# （src/tofrom_time/config.py → parents[2] がプロジェクトルート）
DEFAULT_STATIONS_PATH = Path(__file__).resolve().parents[2] / "config" / "stations.toml"


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
    """stations.toml を読み込む。存在しなければ空の Stations を返す。"""
    target = Path(path) if path else DEFAULT_STATIONS_PATH
    if not target.exists():
        return Stations()

    with target.open("rb") as f:
        data = tomllib.load(f)

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
    """stations.toml の [defaults] と [preferences.*] を読み込む。

    - ``[defaults]`` … 全検索に効く既定ルール（任意）
    - ``[preferences.<行き先>]`` … 行き先別ルール（行き先名がキー）
    """
    target = Path(path) if path else DEFAULT_STATIONS_PATH
    if not target.exists():
        return Rules()

    with target.open("rb") as f:
        data = tomllib.load(f)

    default = None
    if "defaults" in data:
        default = _build_preference("default", data["defaults"])

    by_destination = {
        name: _build_preference(name, body)
        for name, body in data.get("preferences", {}).items()
    }
    return Rules(default=default, by_destination=by_destination)
