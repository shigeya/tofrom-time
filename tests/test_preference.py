"""ルート選択条件のテスト。"""

from tofrom_time.models import Leg, Route, Stop
from tofrom_time.preference import (
    Preference,
    Rules,
    filter_routes,
    merge_preferences,
)


def _route(lines: list[str], stops: list[str]) -> Route:
    legs = tuple(
        Leg(is_walk=(ln == "徒歩"), line=None if ln == "徒歩" else ln)
        for ln in lines
    )
    stop_objs = tuple(Stop(name=s, arrive="10:00", depart="10:00") for s in stops)
    # legs == stops-1 を満たすよう調整
    legs = legs[: len(stop_objs) - 1]
    return Route(
        stops=stop_objs,
        legs=legs,
        depart_time="10:00",
        arrive_time="11:00",
        duration="1時間",
    )


def test_any_linesのいずれかを含めば一致() -> None:
    pref = Preference(name="成田", any_lines=("スカイライナー", "成田エクスプレス"))
    skyliner = _route(["京王線", "ＪＲ山手線", "京成特急スカイライナー51号"], ["A", "B", "C", "D"])
    assert pref.matches(skyliner) is True


def test_any_linesにどれも該当しなければ不一致() -> None:
    pref = Preference(name="成田", any_lines=("スカイライナー", "成田エクスプレス"))
    local = _route(["京王線", "京成本線快速特急"], ["A", "B", "C"])
    assert pref.matches(local) is False


def test_via駅をすべて通ること() -> None:
    pref = Preference(name="羽田", any_lines=("京急",), via=("渋谷",))
    keikyu = _route(
        ["京王井の頭線急行", "ＪＲ山手線", "京急本線特急"],
        ["分倍河原", "渋谷", "品川", "羽田空港"],
    )
    assert pref.matches(keikyu) is True


def test_via駅を通らなければ不一致() -> None:
    pref = Preference(name="羽田", any_lines=("京急",), via=("渋谷",))
    no_shibuya = _route(
        ["都営大江戸線", "京急本線特急"],
        ["分倍河原", "大門", "羽田空港"],
    )
    assert pref.matches(no_shibuya) is False


def test_filter_routesは一致のみ順序保持で返す() -> None:
    pref = Preference(name="成田", any_lines=("スカイライナー",))
    r1 = _route(["京成特急スカイライナー51号"], ["A", "B"])
    r2 = _route(["京成本線快速特急"], ["A", "B"])
    r3 = _route(["京成特急スカイライナー53号"], ["A", "B"])
    assert filter_routes((r1, r2, r3), pref) == (r1, r3)


def test_preferenceがNoneなら全件() -> None:
    r1 = _route(["X線"], ["A", "B"])
    assert filter_routes((r1,), None) == (r1,)


# --- deny_lines / prefer_lines ---------------------------------------------

def test_deny_linesを使うルートは除外() -> None:
    pref = Preference(name="羽田", any_lines=("京急",), deny_lines=("京王線",))
    keio = _route(["京王線快速", "京急本線特急"], ["分倍河原", "品川", "羽田空港"])
    denentoshi = _route(["東急田園都市線", "京急本線特急"], ["溝の口", "品川", "羽田空港"])
    assert pref.matches(keio) is False
    assert pref.matches(denentoshi) is True


def test_京王線禁止は京王新線や井の頭線を巻き込まない() -> None:
    pref = Preference(name="羽田", deny_lines=("京王線",))
    inokashira = _route(["京王井の頭線急行", "京急本線特急"], ["分倍河原", "渋谷", "羽田空港"])
    assert pref.matches(inokashira) is True


def test_prefer_linesは該当を上位へ並べ替え() -> None:
    pref = Preference(name="羽田", any_lines=("京急",), prefer_lines=("田園都市線",))
    keio = _route(["京王井の頭線", "京急本線特急"], ["分倍河原", "渋谷", "羽田空港"])
    denentoshi = _route(["東急田園都市線", "京急本線特急"], ["溝の口", "品川", "羽田空港"])
    # 入力は京王が先でも、田園都市線が上位に来る
    result = filter_routes((keio, denentoshi), pref)
    assert result == (denentoshi, keio)


# --- merge / Rules ----------------------------------------------------------

def test_merge_は_deny_linesを和集合にする() -> None:
    base = Preference(name="default", deny_lines=("高速バス",))
    override = Preference(name="羽田", any_lines=("京急",), deny_lines=("京王線",))
    merged = merge_preferences(base, override)
    assert merged.name == "羽田"
    assert set(merged.deny_lines) == {"高速バス", "京王線"}
    assert merged.any_lines == ("京急",)


def test_Rules_は既定ルールを行き先別にマージする() -> None:
    rules = Rules(
        default=Preference(name="default", deny_lines=("高速バス",)),
        by_destination={"羽田空港": Preference(name="羽田空港", any_lines=("京急",))},
    )
    pref = rules.resolve(prefer=None, show_all=False, destination="羽田空港")
    assert pref is not None
    assert "高速バス" in pref.deny_lines  # 既定ルールが効いている
    assert pref.any_lines == ("京急",)


def test_Rules_は行き先一致が無ければ既定のみ() -> None:
    rules = Rules(default=Preference(name="default", deny_lines=("高速バス",)))
    pref = rules.resolve(prefer=None, show_all=False, destination="大阪")
    assert pref is not None and pref.name == "default"


def test_Rules_未知のprefer名はValueError() -> None:
    import pytest

    rules = Rules(by_destination={"羽田空港": Preference(name="羽田空港")})
    with pytest.raises(ValueError):
        rules.resolve(prefer="未定義", show_all=False, destination="羽田空港")
