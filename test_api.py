from fastapi.testclient import TestClient

from webapp.main import create_app


def test_api_parse_single():
    app = create_app()
    client = TestClient(app)
    resp = client.post('/api/parse', json={'lines': ['INNFOS. Robots[EB/OL]. (2020-01-01) [2020-04-30]. https://innfos.com/']})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]['success'] is True
    assert '[EB/OL]' in data[0]['gbt']


def test_api_parse_batch():
    app = create_app()
    client = TestClient(app)
    lines = [
        'INNFOS. Robots[EB/OL]. (2020-01-01) [2020-04-30]. https://innfos.com/',
        'Yu H B, Liu J G, Liu L Q, et al. Intelligent robotics and applications[J]. Example Journal, 2023, 12(1): 20-30.'
    ]
    resp = client.post('/api/parse', json={'lines': lines})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert all('gbt' in r for r in data)


def test_web_form_bibitem():
    app = create_app()
    client = TestClient(app)
    resp = client.post('/parse', data={
        'references': 'INNFOS. Robots[EB/OL]. (2020-01-01) [2020-04-30]. https://innfos.com/\n',
        'mode': 'bibitem'
    })
    assert resp.status_code == 200
    assert '\\bibitem{' in resp.text
