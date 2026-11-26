"""Build a local review corpus from explicitly sourced factual notes."""
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path

from .load_candidates import load_candidates


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_snapshot(base_path, facts_path, output_path):
    base_path, facts_path, output_path = map(Path, (base_path, facts_path, output_path))
    if output_path.exists():
        raise FileExistsError("Choose a new snapshot directory; existing data is preserved")
    load_candidates(base_path)
    base = json.loads(base_path.read_text(encoding="utf-8"))
    notes = json.loads(facts_path.read_text(encoding="utf-8"))
    additions, evidence = [], []
    ids = {row["poi_id"] for row in base}
    names = {row["name"] for row in base}
    for note in notes["records"]:
        for field in ("source_id", "source_url", "source_date", "name", "category", "address", "evidence_location"):
            if not isinstance(note.get(field), str) or not note[field].strip():
                raise ValueError(f"Missing source fact: {field}")
        if not note["source_url"].startswith("https://lib.ouhai.gov.cn/"):
            raise ValueError("This review importer is restricted to the recorded library publisher")
        if not isinstance(note.get("facts"), list) or not note["facts"] or any(
                not isinstance(value, str) or not value.strip() for value in note["facts"]):
            raise ValueError("Description needs explicit source-supported factual sentences")
        poi_id = "review_" + note["source_id"]
        if poi_id in ids or note["name"] in names:
            raise ValueError("ID/name collision requires an explicit entity review")
        ids.add(poi_id)
        names.add(note["name"])
        row = {
            "poi_id": poi_id,
            "name": note["name"],
            "category": note["category"],
            "address": note["address"],
            "description": " ".join(note["facts"]),
            "opening_hours": note.get("opening_hours"),
            "source_url": note["source_url"],
            "source_ids": [note["source_id"]],
            "source_date": note["source_date"],
            "source_checked_on": notes["checked_on"],
            "is_synthetic": False,
            "original_crs": "UNKNOWN",
            "longitude": None,
            "latitude": None,
            "ticket_info": None,
            "quietness_verified": False,
            "district_verified": False,
            "map_ready": False,
            "entrance_verified": False,
            "entity_identity_status": "PENDING; compare with generic existing records",
            "license_status": notes["license_status"],
            "formal_evaluation_eligible": False,
            "indoor_study_facility": note.get("indoor_study_facility"),
        }
        additions.append(row)
        for field in ("name", "category", "address", "description", "opening_hours", "indoor_study_facility"):
            if row[field] is not None:
                evidence.append({
                    "poi_id": poi_id, "field": field, "value": row[field],
                    "source_url": note["source_url"], "source_date": note["source_date"],
                    "checked_on": notes["checked_on"], "evidence_location": note["evidence_location"],
                    "capture_sha256": sha256(facts_path),
                    "conflicting_source": note.get("conflicting_source") if field == "opening_hours" else None,
                })
    rows = deepcopy(base) + additions
    manifest = {
        "created_at": datetime.now().astimezone().isoformat(),
        "purpose": "local_development_review",
        "formal_evaluation_ready": False,
        "base_path": str(base_path), "base_sha256": sha256(base_path),
        "facts_path": str(facts_path), "facts_sha256": sha256(facts_path),
        "capture_method": notes["capture_method"],
        "license_status": notes["license_status"],
        "base_records": len(base), "added_source_records": len(additions),
        "candidate_records": len(rows), "independently_verified_places": 0,
        "new_verified_entrances": 0,
        "missing_address": sum(not row.get("address") for row in rows),
        "category_counts": dict(Counter(row["category"] for row in rows)),
        "common_text_fields": ["name", "category", "address", "description"],
    }
    output_path.mkdir(parents=True, exist_ok=False)
    for filename, value in (
        ("poi_candidates.json", rows), ("new_field_evidence.json", evidence),
        ("source_facts.json", notes), ("source_manifest.json", manifest),
    ):
        (output_path / filename).write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    load_candidates(output_path / "poi_candidates.json")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("base")
    parser.add_argument("facts")
    parser.add_argument("output")
    args = parser.parse_args()
    print(json.dumps(build_snapshot(args.base, args.facts, args.output), ensure_ascii=False, indent=2))
