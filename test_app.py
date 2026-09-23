import sqlite3
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
        second = client.post('/leads', json={'message': 'My SUV. Saturday works.', 'conversation_id': cid}).json()
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
        result = client.post('/leads', json={'message': 'interior sedan Sunday'}).json()
        assert not result['qualified'] and 'closed Sunday' in result['reply']
        assert client.post(result['booking_url'], json={'name': 'Alex'}).status_code == 409
        fixed = client.post('/leads', json={'message': 'Saturday', 'conversation_id': result['conversation_id']}).json()
        assert fixed['qualified']

def test_concurrent_duplicate_booking(tmp_path):
    with TestClient(create_app(tmp_path / 'test.db')) as client:
        lead = client.post('/leads', json={'message': 'full truck Monday'}).json()
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: client.post(lead['booking_url'], json={'name': 'Sam'}).json(), range(4)))
        assert len({r['booking_id'] for r in results}) == 1
