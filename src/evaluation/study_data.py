"""查询草案和独立标注表的轻量校验；不生成相关性标签。"""
import csv
import json
from pathlib import Path

QUERY_TYPES = {'named_lexical', 'semantic_paraphrase', 'multi_preference', 'hard_constraint'}
QUERY_COLUMNS = ('query_id', 'query_text_zh', 'query_type', 'intent_group_id', 'split',
    'involved_fields', 'constraint_type', 'constraints_json', 'evidence_requirements',
    'evidence_refs', 'usage_status', 'human_review_status', 'formal_eligible', 'design_note')
ANNOTATION_COLUMNS = ('pair_id', 'query_id', 'query_text_zh', 'query_type', 'query_status',
    'poi_id', 'poi_name', 'category', 'address', 'source_fact_text', 'source_url',
    'evidence_ref', 'candidate_status', 'rater_slot', 'annotator_id',
    'semantic_grade', 'semantic_evidence_refs', 'hard_constraint_status',
    'constraint_evidence_refs', 'unknown_reason', 'notes', 'annotated_at')
ADJUDICATION_COLUMNS = ('pair_id', 'query_id', 'poi_id', 'rater_a_grade', 'rater_b_grade',
    'rater_a_constraint_status', 'rater_b_constraint_status', 'final_semantic_grade',
    'final_constraint_status', 'evidence_refs', 'decision_reason', 'adjudicator_id', 'adjudicated_at')
CONSTRAINT_STATUSES = {'met', 'unmet', 'unknown', 'not_applicable'}


def read_queries(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames) or not set(QUERY_COLUMNS) <= set(reader.fieldnames):
            raise ValueError('Incomplete or duplicate query headers')
        rows = list(reader)
    if not rows or any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError('Empty or ragged query table')
    return validate_queries(rows)


def validate_queries(rows):
    ids, texts, groups = set(), set(), {}
    for row in rows:
        if any(k not in row for k in QUERY_COLUMNS):
            raise ValueError('Query schema is incomplete')
        qid, text = row['query_id'], row['query_text_zh'].strip()
        if not qid.strip() or qid in ids or not text or text in texts:
            raise ValueError('Empty or duplicate query ID/text')
        ids.add(qid)
        texts.add(text)
        if row['query_type'] not in QUERY_TYPES or row['split'] not in ('dev_draft', 'review_pool_draft'):
            raise ValueError('Invalid query type or draft split')
        if row['formal_eligible'] != 'false' or row['human_review_status'] != 'pending':
            raise ValueError('Pilot draft cannot be promoted to approved/frozen test data')
        if row['usage_status'] not in ('candidate_only', 'blocked_pending_verification'):
            raise ValueError('Invalid draft usage status')
        if not row['intent_group_id'] or not row['evidence_requirements']:
            raise ValueError('Intent group and evidence requirements are mandatory')
        group = row['intent_group_id']
        if group in groups and groups[group] != row['split']:
            raise ValueError('Same intent group leaks across draft splits')
        groups[group] = row['split']
        if not isinstance(json.loads(row['involved_fields']), list) or not json.loads(row['involved_fields']):
            raise ValueError('Involved fields must be a nonempty list')
        constraint = json.loads(row['constraints_json'])
        if not isinstance(constraint, dict) or not isinstance(json.loads(row['evidence_refs']), list):
            raise ValueError('Invalid structured constraints/evidence references')
        if row['constraint_type'] not in ('none', 'soft', 'hard') or any(
                not isinstance(constraint.get(k), list) for k in ('soft', 'hard')):
            raise ValueError('Constraints require explicit soft/hard arrays')
        if row['query_type'] == 'hard_constraint' and (
            row['constraint_type'] != 'hard' or not constraint.get('hard') or
            row['usage_status'] != 'blocked_pending_verification'):
            raise ValueError('Unverified hard queries must remain blocked')
    return rows


def parse_grade(value):
    if value is None or value == '':
        return None
    if value not in ('0', '1', '2'):
        raise ValueError('Blank means unjudged; grade must be 0/1/2')
    return int(value)


def read_annotations(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        headers = set(reader.fieldnames or [])
        if len(headers) != len(reader.fieldnames or []) or not set(ANNOTATION_COLUMNS) <= headers or headers & {'model', 'model_name', 'rank', 'score', 'retrieval_score'}:
            raise ValueError('Annotation packet must be complete and blind to model/rank/score')
        rows = list(reader)
    seen, pairs = set(), set()
    for row in rows:
        if None in row or any(v is None for v in row.values()):
            raise ValueError('Ragged annotation row')
        key = (row['query_id'], row['poi_id'])
        if not all(key) or not row['pair_id'] or row['pair_id'] in seen or key in pairs:
            raise ValueError('Duplicate or empty annotation pair')
        seen.add(row['pair_id'])
        pairs.add(key)
        grade = parse_grade(row['semantic_grade'])
        if row['hard_constraint_status'] and row['hard_constraint_status'] not in CONSTRAINT_STATUSES:
            raise ValueError('Invalid constraint status')
        if grade is not None and not all(row[k].strip() for k in
                ('annotator_id', 'semantic_evidence_refs', 'annotated_at')):
            raise ValueError('Human rating requires annotator, evidence and date')
        if row['hard_constraint_status'] and not all(row[k].strip() for k in ('annotator_id', 'annotated_at')):
            raise ValueError('Human constraint judgment requires annotator and date')
        if row['hard_constraint_status'] in ('met', 'unmet') and not row['constraint_evidence_refs'].strip():
            raise ValueError('Constraint decision requires explicit evidence')
        if row['hard_constraint_status'] == 'unknown' and not row['unknown_reason'].strip():
            raise ValueError('Unknown constraint needs a recorded evidence gap')
    return rows


def paired_original_grades(first, second):
    """只选两表已独立填写的同一配对；缺失原始评分不补0。"""
    def indexed(rows):
        result = {}
        for row in rows:
            key = (row['query_id'], row['poi_id'])
            if key in result:
                raise ValueError('Duplicate original annotation pair')
            result[key] = row
        return result
    a, b = indexed(first), indexed(second)
    if set(a) != set(b):
        raise ValueError('Original packets must cover identical pairs')
    left, right, pair_ids = [], [], []
    for key in sorted(a):
        x, y = parse_grade(a[key]['semantic_grade']), parse_grade(b[key]['semantic_grade'])
        if x is None or y is None:
            continue
        if not a[key]['annotator_id'] or not b[key]['annotator_id'] or a[key]['annotator_id'] == b[key]['annotator_id']:
            raise ValueError('Two distinct actual annotators are required')
        left.append(x)
        right.append(y)
        pair_ids.append(a[key]['pair_id'])
    return left, right, pair_ids


def constraint_eligible(status, *, has_hard_constraints):
    if status not in CONSTRAINT_STATUSES:
        raise ValueError('Explicit reviewed constraint status required')
    return status == 'met' if has_hard_constraints else status == 'not_applicable'
