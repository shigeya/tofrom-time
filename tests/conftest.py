"""テスト共通のフィクスチャ。"""

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def depart_html() -> str:
    """出発時刻指定（type=1）の保存済み検索結果 HTML。"""
    return (FIXTURES / "raw_result.html").read_text(encoding="utf-8")


@pytest.fixture
def arrive_html() -> str:
    """到着時刻指定（type=4）の保存済み検索結果 HTML。"""
    return (FIXTURES / "raw_result_arrive.html").read_text(encoding="utf-8")
