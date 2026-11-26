"""Contract test: the collector (Python) and the phone app (JavaScript) must score and tag
stories identically. Both read tests/fixtures/scoring_cases.json (the JS side is in
tests/js/scoring_contract.test.mjs). If you change RANKING/TAGS on purpose, regenerate the
fixture with:  python -m tests.test_scoring_contract
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from digest import config
from digest.models import Item
from digest.rank import score, tags

FIXTURE = Path(__file__).parent / "fixtures" / "scoring_cases.json"
NOW = datetime(2026, 11, 26, 6, 0, tzinfo=timezone.utc)


def _item(case):
    return Item(key="k", url="https://e", source="s", **case["item"])


def test_fixture_matches_current_rules():
    data = json.loads(FIXTURE.read_text())
    assert data["ranking"] == config.RANKING, "RANKING changed: regenerate the fixture (see docstring)"
    assert data["tags"] == config.TAGS and data["tag_exclude"] == config.TAG_EXCLUDE


def test_python_scores_match_contract():
    for case in json.loads(FIXTURE.read_text())["cases"]:
        got = score(_item(case), now=NOW)
        assert {k: got[k] for k in ("importance", "urgency", "quadrant")} == case["expected"], case["item"]["title"]
        assert tags(_item(case)) == case["tags"], case["item"]["title"]


if __name__ == "__main__":  # regenerate after an intentional rules change
    data = json.loads(FIXTURE.read_text())
    data.update(ranking=config.RANKING, tags=config.TAGS, tag_exclude=config.TAG_EXCLUDE)
    for case in data["cases"]:
        s = score(_item(case), now=NOW)
        case["expected"] = {k: s[k] for k in ("importance", "urgency", "quadrant")}
        case["tags"] = tags(_item(case))
    FIXTURE.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print("fixture regenerated")
