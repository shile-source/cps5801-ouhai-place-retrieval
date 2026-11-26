"""Synthetic importer tests preserve historical data and unknown status."""
import json
import pytest

from src.data.development_snapshot import build_snapshot
from src.data.load_candidates import load_candidates


@pytest.fixture
def inputs(tmp_path):
    base = tmp_path / "base.json"
    base.write_text(json.dumps([{
        "poi_id": "synthetic_old", "name": "合成旧记录", "category": "合成类别",
        "address": "", "description": "合成测试", "is_synthetic": False,
    }]), encoding="utf-8")
    facts = tmp_path / "facts.json"
    facts.write_text(json.dumps({
        "checked_on": "2026-11-06", "license_status": "UNKNOWN",
        "capture_method": "Explicitly synthetic test facts",
        "records": [{
            "source_id": "synthetic_new", "source_url": "https://lib.ouhai.gov.cn/synthetic-test",
            "source_date": "2020-01-01", "name": "合成新记录", "category": "合成类别",
            "address": "合成地址", "facts": ["合成设施事实。"],
            "evidence_location": "Synthetic paragraph",
            "conflicting_source": {"opening_hours": "Synthetic older claim"},
            "opening_hours": "Synthetic schedule",
        }],
    }), encoding="utf-8")
    return base, facts, tmp_path / "result"


def test_snapshot_preserves_base_and_evidence_without_promoting_verification(inputs):
    base, facts, output = inputs
    before = base.read_bytes()
    manifest = build_snapshot(base, facts, output)
    assert base.read_bytes() == before
    rows = json.loads((output / "poi_candidates.json").read_text(encoding="utf-8"))
    assert rows[0] == json.loads(base.read_text(encoding="utf-8"))[0]
    assert len(load_candidates(output / "poi_candidates.json")) == 2
    assert rows[1]["longitude"] is None and rows[1]["original_crs"] == "UNKNOWN"
    assert rows[1]["map_ready"] is False and rows[1]["quietness_verified"] is False
    assert manifest["formal_evaluation_ready"] is False
    evidence = json.loads((output / "new_field_evidence.json").read_text(encoding="utf-8"))
    assert next(row for row in evidence if row["field"] == "opening_hours")["conflicting_source"]
    with pytest.raises(FileExistsError):
        build_snapshot(base, facts, output)


@pytest.mark.parametrize("change", ["same_name", "duplicate_id", "missing_evidence", "other_publisher"])
def test_import_rejects_unreviewed_collisions_and_unsourced_facts(inputs, change):
    base, facts, output = inputs
    data = json.loads(facts.read_text(encoding="utf-8"))
    if change == "same_name":
        data["records"][0]["name"] = "合成旧记录"
    elif change == "duplicate_id":
        data["records"].append(dict(data["records"][0]))
    elif change == "missing_evidence":
        data["records"][0]["evidence_location"] = ""
    else:
        data["records"][0]["source_url"] = "https://example.invalid/"
    facts.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        build_snapshot(base, facts, output)
    assert not output.exists()
