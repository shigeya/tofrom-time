"""ルート選択条件（行き先ごとに使いたい列車・経由・禁止・優先）。"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import Route


@dataclass(frozen=True)
class Preference:
    """ルートの絞り込み・並べ替え条件。

    ハード条件（満たさないルートは除外）:

    - ``any_lines``: いずれかの区間の路線名にこの語のどれかを含むこと。
    - ``via``: これらの駅をすべて通ること（駅名の部分一致）。
    - ``deny_lines``: これらの語を路線名に含む区間を **使わない** こと（例: ``("京王線",)``）。

    ソフト条件（除外はしないが並び順に影響）:

    - ``prefer_lines``: これらの語を含むルートを上位に並べる（例: ``("田園都市線",)``）。

    検索オプション:

    - ``use_limited_express``: 検索時に有料特急を候補へ含める（ex=1）。
    """

    name: str
    any_lines: tuple[str, ...] = ()
    via: tuple[str, ...] = ()
    deny_lines: tuple[str, ...] = ()
    prefer_lines: tuple[str, ...] = ()
    use_limited_express: bool = False

    def matches(self, route: Route) -> bool:
        """ルートがハード条件をすべて満たすか。"""
        if self.any_lines and not self._uses_any(route, self.any_lines):
            return False
        if self.via and not self._via_matches(route):
            return False
        if self.deny_lines and self._uses_any(route, self.deny_lines):
            return False
        return True

    def rank(self, route: Route) -> int:
        """並べ替え用の優先度（小さいほど上位）。"""
        if self.prefer_lines and self._uses_any(route, self.prefer_lines):
            return 0
        return 1

    @staticmethod
    def _uses_any(route: Route, keywords: tuple[str, ...]) -> bool:
        lines = [leg.line or "" for leg in route.legs]
        return any(kw in line for kw in keywords for line in lines)

    def _via_matches(self, route: Route) -> bool:
        names = [stop.name for stop in route.stops]
        return all(
            any(station in name for name in names) for station in self.via
        )


def merge_preferences(base: Preference, override: Preference) -> Preference:
    """既定ルール ``base`` の上に行き先別ルール ``override`` を重ねる。

    - ``any_lines`` / ``via`` / ``prefer_lines``: override が指定されていれば優先、
      無ければ base を使う。
    - ``deny_lines``: 両方を合わせる（和集合）。
    - ``use_limited_express``: どちらかが true なら true。
    """
    return Preference(
        name=override.name,
        any_lines=override.any_lines or base.any_lines,
        via=override.via or base.via,
        deny_lines=_dedup(base.deny_lines + override.deny_lines),
        prefer_lines=override.prefer_lines or base.prefer_lines,
        use_limited_express=base.use_limited_express or override.use_limited_express,
    )


def _dedup(items: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(items))


@dataclass(frozen=True)
class Rules:
    """既定ルールと行き先別ルールの集合。"""

    default: Preference | None = None
    by_destination: dict[str, Preference] = field(default_factory=dict)

    def resolve(
        self, *, prefer: str | None, show_all: bool, destination: str
    ) -> Preference | None:
        """適用するルールを決める。

        優先順位: ``show_all`` > ``prefer`` 明示 > 行き先による自動適用。
        既定ルールがあれば、行き先別ルールにマージして返す。
        未知の ``prefer`` 名は ValueError。
        """
        if show_all:
            return None

        if prefer:
            if prefer not in self.by_destination:
                available = ", ".join(self.by_destination) or "（なし）"
                raise ValueError(f"未知の条件名: {prefer!r}（利用可能: {available}）")
            specific: Preference | None = self.by_destination[prefer]
        else:
            specific = self.by_destination.get(destination)

        if self.default and specific:
            return merge_preferences(self.default, specific)
        return specific or self.default


def filter_routes(
    routes: tuple[Route, ...], preference: Preference | None
) -> tuple[Route, ...]:
    """条件に合うルートを返す。

    ハード条件で除外し、``prefer_lines`` があれば該当ルートを上位へ安定ソートする。
    ``preference`` が ``None`` のときは全件そのまま返す。
    """
    if preference is None:
        return routes
    matched = [route for route in routes if preference.matches(route)]
    if preference.prefer_lines:
        matched.sort(key=preference.rank)  # 安定ソート
    return tuple(matched)
