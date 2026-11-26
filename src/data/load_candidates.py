"""只读加载候选快照；不升级地理/属性验证状态。"""
import json
from pathlib import Path
from .poi import POI


def load_candidates(path: str | Path) -> tuple[POI, ...]:
    rows = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(rows, list):
        raise ValueError('Expected a JSON array of candidate records')
    result = []
    for row in rows:
        if not isinstance(row, dict) or row.get('is_synthetic') is not False:
            raise ValueError('This loader accepts explicitly real candidates only')
        fields = {k: row.get(k, '') for k in ('poi_id', 'name', 'category', 'address', 'description')}
        if any(not isinstance(v, str) for v in fields.values()):
            raise ValueError('Retrieval text fields must be strings; missing attributes must not be invented')
        result.append(POI(**fields, is_synthetic=False))
    return tuple(result)
