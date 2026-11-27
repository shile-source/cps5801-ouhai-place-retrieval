import json
from src.demo import runtime_policy


def test_recovery_requires_the_exact_validated_source_and_configuration(tmp_path,monkeypatch):
    monkeypatch.setattr(runtime_policy,'JOB',tmp_path)
    monkeypatch.setattr(runtime_policy,'STOP',tmp_path/'runtime_stop.json')
    monkeypatch.setattr(runtime_policy,'identity',lambda:{'synthetic_configuration':'current'})
    assert runtime_policy.validated() is False
    receipt=tmp_path/'validation.json'
    receipt.write_text(json.dumps({'status':'passed_two_loads_and_two_healthy_idle_releases',
                                  'identity':{'synthetic_configuration':'old'}}),encoding='utf-8')
    assert runtime_policy.validated() is False
    receipt.write_text(json.dumps({'status':'passed_two_loads_and_two_healthy_idle_releases',
                                  'identity':{'synthetic_configuration':'current'}}),encoding='utf-8')
    assert runtime_policy.validated() is True


def test_a_new_failure_prevents_restart_even_after_a_successful_repair(tmp_path,monkeypatch):
    monkeypatch.setattr(runtime_policy,'JOB',tmp_path)
    monkeypatch.setattr(runtime_policy,'STOP',tmp_path/'runtime_stop.json')
    monkeypatch.setattr(runtime_policy,'identity',lambda:{'synthetic':True})
    (tmp_path/'validation.json').write_text(json.dumps({
        'status':'passed_two_loads_and_two_healthy_idle_releases','identity':{'synthetic':True}}),encoding='utf-8')
    runtime_policy.STOP.write_text('{}',encoding='utf-8')
    assert runtime_policy.validated() is False
