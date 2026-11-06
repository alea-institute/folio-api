"""Server-rendered ontology selection and related-item navigation."""

from html.parser import HTMLParser
import re

import pytest


class Tags(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def find(self, tag, **attrs):
        return [a for t, a in self.tags if t == tag and all(a.get(k) == v for k, v in attrs.items())]


def test_folio_page(client):
    response = client.get('/explore/tree')
    assert response.status_code == 200
    html = response.text
    tags = Tags(html)
    assert '<h1 class="text-3xl font-bold">FOLIO Ontology Explorer</h1>' in html
    assert not tags.find('div', **{'aria-label': 'Ontology view'})
    header = re.search(r'<header\b[^>]*>(.*?)</header>', html, re.S)[1]
    switches = Tags(header).find('a', href='/explore/tree?ontology=canon')
    assert len(switches) == 1
    assert switches[0]['aria-label'] == 'Switch to the Catholic Semantic Canon'
    assert switches[0]['title'] == 'Catholic Semantic Canon'
    assert 'text-[rgb(38_88_142)]' in switches[0]['class'].split()
    switch = re.search(r'<a\b[^>]*href="/explore/tree\?ontology=canon"[^>]*><span aria-hidden="true">\+</span></a>', header)
    assert switch
    assert 'Catholic Semantic Canon' not in re.sub(r'<[^>]+>', '', header)
    assert header.index('Learn More</a>') < switch.start()
    assert not tags.find('a', **{'aria-current': 'page'})
    assert tags.find('button', id='tab-graph')
    assert 'FOLIO Website' in html and 'Learn More' in html


def test_canon_page(client):
    response = client.get('/explore/tree?ontology=canon')
    assert response.status_code == 200
    html = response.text
    tags = Tags(html)
    assert '<h1 class="text-3xl font-bold">Catholic Semantic Canon</h1>' in html
    assert '<title>Catholic Semantic Canon</title>' in html
    assert tags.find('meta', name='author', content='Catholic Semantic Canon')
    assert not tags.find('div', **{'aria-label': 'Ontology view'})
    header = re.search(r'<header\b[^>]*>(.*?)</header>', html, re.S)[1]
    switches = Tags(header).find('a', href='/explore/tree')
    assert len(switches) == 1
    assert switches[0]['aria-label'] == 'Switch to FOLIO'
    assert switches[0]['title'] == 'FOLIO'
    assert 'text-[rgb(38_88_142)]' in switches[0]['class'].split()
    switch = re.search(r'<a\b[^>]*href="/explore/tree"[^>]*><span aria-hidden="true">\+</span></a>', header)
    assert switch
    assert 'FOLIO' not in header.replace(switch[0], '')
    assert switch[0].count('FOLIO') == 2
    assert not tags.find('a', **{'aria-current': 'page'})
    assert not tags.find('button', id='tab-graph')
    assert 'grid-cols-1' in tags.find('div', id='detail-tabs')[0]['class']
    assert 'FOLIO Website' not in html and 'Learn More' not in html
    assert 'FOLIO' not in re.search(r'<head>(.*?)</head>', html, re.S)[1]
    assert 'FOLIO' not in re.search(r'<h1\b[^>]*>(.*?)</h1>', html, re.S)[1]
    assert 'FOLIO' not in tags.find('input', id='explore-search-input')[0]['placeholder']
    assert tags.find('div', **{'data-ontology': 'canon', 'data-tree-state': 'ready'})
    # Switching views always starts at the other ontology's roots.
    assert tags.find('a', href='/explore/tree')
    assert not tags.find('a', href='/explore/tree?ontology=canon')


def test_unknown_ontology(client):
    assert client.get('/explore/tree?ontology=bogus').status_code == 404


@pytest.mark.parametrize('state,message', [
    ('loading', 'Catholic Semantic Canon is loading'),
    ('failed', 'Catholic Semantic Canon is unavailable'),
    ('disabled', 'Catholic Semantic Canon is unavailable'),
])
def test_canon_not_ready(client, state, message):
    registry = client.app.state.ontologies
    previous_state = registry.canon_state
    previous_entry = registry.entries.pop('canon', None)
    registry.canon_state = state
    try:
        folio_response = client.get('/explore/tree')
        assert folio_response.status_code == 200
        assert 'aria-label="Ontology view"' not in folio_response.text
        assert not Tags(folio_response.text).find('a', href='/explore/tree?ontology=canon')
        assert not Tags(folio_response.text).find('a', **{'aria-label': 'Switch to the Catholic Semantic Canon'})
        assert 'id="tab-graph"' in folio_response.text
        response = client.get('/explore/tree?ontology=canon')
        assert response.status_code == 200
        html = response.text
        tags = Tags(html)
        assert 'aria-label="Ontology view"' not in html
        assert not tags.find('a', **{'aria-label': 'Switch to FOLIO'})
        header = re.search(r'<header\b[^>]*>(.*?)</header>', html, re.S)[1]
        assert not Tags(header).find('a', href='/explore/tree')
        assert html.count(f'<p role="status">{message}</p>') == 2
        assert tags.find('div', **{'data-tree-state': 'blocked'})
        assert tags.find('a', href='/explore/tree')
        for control in ['explore-search-input', 'explore-search-button', 'expand-tree-depth',
                        'expand-all-tree', 'collapse-all-tree', 'collapse-tree-one-level']:
            tag = 'input' if control == 'explore-search-input' else 'button'
            assert 'disabled' in tags.find(tag, id=control)[0]
    finally:
        registry.canon_state = previous_state
        if previous_entry is not None:
            registry.entries['canon'] = previous_entry


PRESENT = {'iri': 'https://ontology.catholicos.catholic/present', 'label': 'Present relation', 'definition': ''}
ABSENT = {'iri': 'https://example.org/absent', 'label': 'Absent relation', 'definition': ''}
RELATIONS = [PRESENT, ABSENT]


def panel_context(kind, relation):
    data = {'iri': 'https://ontology.catholicos.catholic/selected', 'label': 'Selected', 'definition': ''}
    if kind == 'class':
        context = {'class_data': data, 'folio_graph': {item['iri']: item for item in RELATIONS}}
        if relation in ('domain_properties', 'range_properties'):
            context[relation] = RELATIONS
        else:
            data[relation] = [item['iri'] for item in RELATIONS] if relation == 'see_also' else RELATIONS
    else:
        context = {'prop_data': data}
        data[relation] = PRESENT if relation == 'inverse' else RELATIONS
    return context


PANEL_RELATIONS = [
    ('class', relation) for relation in ('parents', 'children', 'see_also', 'domain_properties', 'range_properties')
] + [
    ('property', relation) for relation in ('parents', 'children', 'inverse', 'domain_classes', 'range_classes')
]


@pytest.mark.parametrize('kind,relation', PANEL_RELATIONS)
def test_canon_panel_relations(client, kind, relation):
    env = client.app.state.templates.env
    template = env.get_template(f'components/{kind}_details.html')
    context = panel_context(kind, relation)
    # An inverse is a single item, so render once for each membership result.
    for inverse_item in RELATIONS if relation == 'inverse' else [None]:
        if inverse_item:
            context['prop_data']['inverse'] = inverse_item
        html = template.render(**context, ontology_key='canon', in_ontology=lambda iri: iri == PRESENT['iri'])
        anchors = Tags(html).find('a')
        assert not any(a.get('href', '').endswith('/html') for a in anchors)
        selections = [a.get('onclick', '') for a in anchors]
        if inverse_item != ABSENT:
            assert any('selectNodeByIri' in onclick and PRESENT['iri'] in onclick for onclick in selections)
        assert not any(ABSENT['iri'] in onclick for onclick in selections)
        if relation != 'inverse' or inverse_item == ABSENT:
            assert re.search(r'<span>\s*Absent relation\s*</span>', html)


@pytest.mark.parametrize('kind,relation', PANEL_RELATIONS)
def test_folio_panel_links_and_missing_context(client, kind, relation):
    template = client.app.state.templates.env.get_template(f'components/{kind}_details.html')
    context = panel_context(kind, relation)
    html = template.render(**context, ontology_key='folio')
    assert html == template.render(**context)
    anchors = Tags(html).find('a')
    if relation in ('see_also', 'domain_properties', 'range_properties', 'domain_classes', 'range_classes'):
        prefix = '/' if relation in ('domain_properties', 'range_properties') else ''
        for item in RELATIONS:
            assert any(a.get('href') == prefix + item['iri'] + '/html' for a in anchors)
    else:
        for item in [PRESENT] if relation == 'inverse' else RELATIONS:
            assert any(a.get('onclick') == f"selectNodeByIri('{item['iri']}'); return false;" for a in anchors)
