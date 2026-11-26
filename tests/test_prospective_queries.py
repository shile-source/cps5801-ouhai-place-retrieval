import json
import threading
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import pytest
from src.evaluation.prospective_queries import QueryDraft
from src.demo.prospective_query_server import handler


def make(tmp_path):
    corpus = tmp_path / 'corpus.json'
    corpus.write_text('[]', encoding='utf-8')
    return QueryDraft(tmp_path / 'session', corpus), corpus


def synthetic():
    return {'queries': [f'synthetic test request {i}' for i in range(30)],
            'author_code': 'synthetic', 'rank_exposure': 'unseen', 'ai_use': 'none', 'confirmed': True}


def test_resume_lock_and_bound_source(tmp_path):
    draft, corpus = make(tmp_path)
    assert not draft.state()['locked']
    value = synthetic()
    draft.save(value)
    assert QueryDraft(draft.directory, corpus).state()['draft']['queries'] == value['queries']
    result = draft.save(value, True)
    assert result['locked'] and result['provenance_verified'] is False
    with pytest.raises(ValueError):
        draft.save(value)
    corpus.write_text('[1]', encoding='utf-8')
    with pytest.raises(ValueError):
        QueryDraft(draft.directory, corpus)


def test_no_false_submission_or_duplicate_queries(tmp_path):
    draft, _ = make(tmp_path)
    for changes in ({'confirmed': False}, {'queries': ['same'] * 30}, {'queries': [''] * 30}, {'rank_exposure': ''}):
        with pytest.raises(ValueError):
            draft.save({**synthetic(), **changes}, True)
    assert not draft.log.exists() and not draft.final.exists()


def test_http_requires_origin_token_and_has_no_model_routes(tmp_path):
    draft, _ = make(tmp_path)
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler(draft))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    try:
        with urlopen(base + '/api/state') as response:
            state = json.load(response)
        headers = {'Content-Type': 'application/json', 'Origin': base, 'X-Query-Token': state['request_token']}
        with pytest.raises(HTTPError) as error:
            urlopen(Request(base + '/api/draft', data=b'{}', headers={'Content-Type': 'application/json'}))
        assert error.value.code == 403
        with urlopen(Request(base + '/api/draft', data=json.dumps(synthetic()).encode(), headers=headers)) as response:
            assert json.load(response)['draft']['author_code'] == 'synthetic'
        with pytest.raises(HTTPError) as error:
            urlopen(Request(base + '/api/evaluate', data=b'{}', headers=headers))
        assert error.value.code == 404
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
