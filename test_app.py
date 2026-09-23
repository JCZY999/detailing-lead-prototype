import sqlite3
import json
import pytest
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from app import create_app

def test_end_to_end_and_persistence(tmp_path):
    path = tmp_path / 'test.sqlite3'
    with TestClient(create_app(path)) as client:
        first = client.post('/leads', json={'message': 'I want an interior detail this weekend.'}).json()
        assert '$149' in first['reply'] and 'Saturday' in first['reply']
        assert not first['qualified']
        cid = first['conversation_id']
        assert client.get(first['booking_url']).status_code == 200
        assert client.post(first['booking_url'], json={'name': 'Alex'}).status_code == 409
        second = client.post('/leads', json={'message': 'My Toyota SUV. Saturday works.', 'conversation_id': cid}).json()
        assert second['qualified']
        booking = client.post(first['booking_url'], json={'name': 'Alex'}).json()
        assert booking['simulated']
        assert client.post(first['booking_url'], json={'name': 'Alex'}).json() == booking
    with TestClient(create_app(path)) as restarted:
        saved = restarted.get('/conversations/' + cid).json()
        assert len(saved['messages']) == 4
        assert saved['booking']['id'] == booking['booking_id']
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT COUNT(*) FROM bookings').fetchone()[0] == 1

def test_closed_day_unknown_and_validation(tmp_path):
    with TestClient(create_app(tmp_path / 'test.db')) as client:
        for message in ('', '   ', 'x' * 2001):
            assert client.post('/leads', json={'message': message}).status_code == 422
        assert client.post('/leads', json={'message': 'hi', 'conversation_id': 'missing'}).status_code == 404
        assert client.get('/book/missing').status_code == 404
        result = client.post('/leads', json={'message': 'interior Honda sedan Sunday'}).json()
        assert not result['qualified'] and 'closed Sunday' in result['reply']
        assert client.post(result['booking_url'], json={'name': 'Alex'}).status_code == 409
        fixed = client.post('/leads', json={'message': 'Saturday', 'conversation_id': result['conversation_id']}).json()
        assert fixed['qualified']

def test_concurrent_duplicate_booking(tmp_path):
    with TestClient(create_app(tmp_path / 'test.db')) as client:
        lead = client.post('/leads', json={'message': 'full Ford truck Monday'}).json()
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: client.post(lead['booking_url'], json={'name': 'Sam'}).json(), range(4)))
        assert len({r['booking_id'] for r in results}) == 1

@pytest.mark.parametrize('message,total', [
    ('interior Toyota sedan Saturday', 149),
    ('interior BMW SUV Saturday', 204),
    ('interior Porsche SUV Saturday', 224),
    ('exterior Mercedes van Monday', 134),
    ('full Chevy truck Friday', 259),
    ('full Tesla minivan Tuesday', 309),
])
def test_price_matches_booking(tmp_path, message, total):
    with TestClient(create_app(tmp_path / 'prices.db')) as client:
        lead = client.post('/leads', json={'message': message}).json()
        assert lead['qualified']
        assert lead['profile']['quote']['total_usd'] == total
        assert f'${total}' in lead['reply']
        assert client.post(lead['booking_url'], json={'name': 'Test'}).status_code == 200
        saved = client.get('/conversations/' + lead['conversation_id']).json()
        details = json.loads(saved['booking']['details'])
        assert details['price_usd'] == total == details['quote']['total_usd']

def test_brand_required_correction_and_snapshot(tmp_path):
    with TestClient(create_app(tmp_path / 'prices.db')) as client:
        lead = client.post('/leads', json={'message': 'interior SUV Saturday'}).json()
        cid = lead['conversation_id']
        assert not lead['qualified'] and lead['profile']['quote'] is None
        assert client.post(lead['booking_url'], json={'name': 'Test'}).status_code == 409
        def say(message):
            return client.post('/leads', json={'message': message, 'conversation_id': cid}).json()
        assert say('BMW')['profile']['quote']['total_usd'] == 204
        assert say('Toyota')['profile']['quote']['total_usd'] == 184
        assert not say('other brand')['qualified']
        assert client.post(lead['booking_url'], json={'name': 'Test'}).status_code == 409
        assert say('Porsche')['profile']['quote']['total_usd'] == 224
        client.post(lead['booking_url'], json={'name': 'Test'})
        assert say('Toyota sedan')['profile']['quote']['total_usd'] == 149
        stored = client.get('/conversations/' + cid).json()
        assert json.loads(stored['booking']['details'])['price_usd'] == 224
        catalog = client.get('/pricing').json()
        assert len(catalog['brands']) == 36
        assert len(catalog['vehicle_adjustments']) == 9
