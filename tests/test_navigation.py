"""Synthetic records only; URI encoding and evidence separation regressions."""
from copy import deepcopy
from urllib.parse import parse_qs, urlsplit
import pytest
from src.demo.navigation import destination, load_notes, map_search_links, source_url


def synthetic_notes():
    return {'synthetic_place':{'poi_id':'synthetic_place','name':'synthetic named place',
            'address':'synthetic new address','source_url':'https://example.org/synthetic-note',
            'checked_on':'synthetic-date','publication_date':'synthetic-date'}}


def test_navigation_supplement_never_changes_retrieval_record():
    note = synthetic_notes()['synthetic_place']
    record = {'poi_id': note['poi_id'], 'name': note['name'], 'address': 'synthetic old address',
              'description': 'synthetic frozen retrieval text', 'source_url': 'https://example.org/synthetic'}
    original = deepcopy(record)
    result = destination(record, {note['poi_id']: note})
    assert record == original
    assert result['has_supplement'] and result['address'] == note['address']
    assert result['snapshot_address'] == original['address']
    assert result['entrance_verified'] is False


def test_matching_id_without_matching_identity_does_not_attach_note():
    notes = synthetic_notes()
    result = destination({'poi_id': 'synthetic_place', 'name': 'different synthetic entity',
                          'address': 'synthetic address', 'source_url': 'javascript:bad()'}, notes)
    assert not result['has_supplement']
    assert result['address'] == 'synthetic address'
    assert result['address_source_url'] == ''


def test_unknown_address_uses_name_instead_of_fabricated_coordinates():
    result = destination({'poi_id': 'synthetic', 'name': 'synthetic park', 'address': '未知'}, {})
    assert result['address'] == ''
    assert parse_qs(urlsplit(result['search_links']['baidu']).query)['query'] == ['synthetic park']
    assert 'location' not in parse_qs(urlsplit(result['search_links']['baidu']).query)


def test_provider_urls_preserve_query_without_parameter_injection():
    query = '模拟地点 &region=elsewhere #?'
    links = map_search_links(query)
    baidu = parse_qs(urlsplit(links['baidu']).query)
    amap = parse_qs(urlsplit(links['amap']).query)
    assert baidu['query'] == [query] and baidu['region'] == ['瓯海区']
    assert amap['keyword'] == ['温州市瓯海区 ' + query] and amap['city'] == ['温州']
    assert not urlsplit(links['baidu']).fragment


@pytest.mark.parametrize('url', ['javascript:alert(1)', 'file:///C:/private', 'https://user:password@example.org', 'https://[broken'])
def test_unsafe_source_urls_are_not_published(url):
    assert source_url(url) == ''


def test_absent_navigation_supplement_is_optional_not_fabricated(tmp_path,monkeypatch):
    monkeypatch.setattr('src.demo.navigation.NOTE',tmp_path/'missing.json')
    assert load_notes()=={}
