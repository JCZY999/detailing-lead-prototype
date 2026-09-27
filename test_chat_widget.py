from pathlib import Path
from fastapi.testclient import TestClient
from app import create_app
import pytest


def test_unconfigured_widget_is_disabled(tmp_path, monkeypatch):
    monkeypatch.delenv('AI_GROWTH_ENGINE_API_URL', raising=False)
    monkeypatch.delenv('AI_GROWTH_ENGINE_BUSINESS_ID', raising=False)
    with TestClient(create_app(tmp_path / 'widget.db')) as client:
        response = client.get('/api/chat-widget/config')
        assert response.json() == {'enabled': False}
        assert response.headers['cache-control'] == 'no-store'


@pytest.mark.parametrize('url', ['http://example.com', 'https://user:secret@example.com', 'javascript:alert(1)', 'https://example.com?key=secret'])
def test_invalid_config_fails_closed(tmp_path, monkeypatch, url):
    monkeypatch.setenv('AI_GROWTH_ENGINE_API_URL', url)
    monkeypatch.setenv('AI_GROWTH_ENGINE_BUSINESS_ID', '00000000-0000-0000-0000-000000000001')
    with TestClient(create_app(tmp_path / 'widget.db')) as client:
        assert client.get('/api/chat-widget/config').json() == {'enabled': False}


def test_config_exposes_only_public_routing_values(tmp_path, monkeypatch):
    monkeypatch.setenv('AI_GROWTH_ENGINE_API_URL', 'https://api.example.com/')
    monkeypatch.setenv('AI_GROWTH_ENGINE_BUSINESS_ID', '00000000-0000-0000-0000-000000000001')
    monkeypatch.setenv('SOME_PRIVATE_KEY', 'never-return-this')
    with TestClient(create_app(tmp_path / 'widget.db')) as client:
        assert client.get('/api/chat-widget/config').json() == {'enabled': True,
            'api_url': 'https://api.example.com', 'business_id': '00000000-0000-0000-0000-000000000001'}


def test_widget_installed_without_replacing_existing_features(tmp_path):
    with TestClient(create_app(tmp_path / 'widget.db')) as client:
        for path in ['/', '/services', '/pricing']:
            response = client.get(path)
            assert response.status_code == 200
            assert 'data-config-url="/api/chat-widget/config"' in response.text
        assert 'id="chat"' in client.get('/').text
        assert 'id="brand-price"' in client.get('/').text
