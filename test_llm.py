"""Offline adapter/integration tests. Mocked provider tests are NOT live AI tests."""
import json
import httpx
import pytest
from fastapi.testclient import TestClient
from app import create_app
from llm import OpenAIConversation, ExtractedTurn, validate_turn

def turn(**updates):
    data = dict(service='interior', brand='BMW', model='X5', vehicle='suv',
                day=None, weekend_requested=True, acknowledgement='I can help with your interior detailing request.')
    return {**data, **updates}

@pytest.fixture(autouse=True)
def environment(monkeypatch):
    monkeypatch.setenv('LLM_MODE', 'auto')
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)

def test_realistic_flow_with_mocked_provider(tmp_path, monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-placeholder-not-a-real-key')
    calls=[]
    responses=[turn(), turn(day='sunday'), turn(day='saturday'), turn(service='exterior', day='saturday')]
    def fake_post(url, **kwargs):
        assert url == 'https://api.openai.com/v1/responses'
        payload=kwargs['json']
        assert payload['store'] is False
        calls.append(json.loads(payload['input'][0]['content']))
        return httpx.Response(200, request=httpx.Request('POST',url), json={
            'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(responses.pop(0))}]}]})
    monkeypatch.setattr('llm.httpx.post', fake_post)
    with TestClient(create_app(tmp_path/'ai.db')) as client:
        first=client.post('/leads',json={'message':'My BMW X5 seats are messy after a road trip. Can you help this weekend?'}).json()
        cid=first['conversation_id']
        assert first['mode']=='openai' and not first['qualified']
        assert '$204' in first['reply']
        second=client.post('/leads',json={'conversation_id':cid,'message':'Sunday works best.'}).json()
        assert not second['qualified'] and 'closed Sunday' in second['reply']
        assert client.post(first['booking_url'],json={'name':'Alex Demo'}).status_code==409
        third=client.post('/leads',json={'conversation_id':cid,'message':'Okay, Saturday instead.'}).json()
        assert third['qualified'] and third['profile']['day']=='saturday'
        fourth=client.post('/leads',json={'conversation_id':cid,'message':'Actually, just the outside, not the interior.'}).json()
        assert fourth['profile']['service']=='exterior' and '$124' in fourth['reply']
        assert len(calls[3]['recent_history'])==6
        assert calls[3]['current_profile']['day']=='saturday'
        assert client.post(first['booking_url'],json={'name':'Alex Demo'}).status_code==200
        saved=client.get('/conversations/'+cid).json()
        assert len(saved['messages'])==8
        assert json.loads(saved['booking']['details'])['price_usd']==124

@pytest.mark.parametrize('failure', ['timeout','unauthorized','incomplete','invalid-json','refusal'])
def test_provider_failures_do_not_save_fake_conversations(tmp_path, monkeypatch, failure):
    monkeypatch.setenv('OPENAI_API_KEY','test-placeholder-not-a-real-key')
    def fake_post(url, **kwargs):
        if failure=='timeout': raise httpx.ReadTimeout('timeout')
        data={'status':'completed','output':[]}
        if failure=='incomplete': data['status']='incomplete'
        if failure=='invalid-json': data['output']=[{'type':'message','content':[{'type':'output_text','text':'not json'}]}]
        return httpx.Response(401 if failure=='unauthorized' else 200,request=httpx.Request('POST',url),json=data)
    monkeypatch.setattr('llm.httpx.post',fake_post)
    dbpath=tmp_path/'error.db'
    with TestClient(create_app(dbpath)) as client:
        response=client.post('/leads',json={'message':'Hi'})
        assert response.status_code==503
        assert 'test-placeholder' not in response.text
    import sqlite3
    with sqlite3.connect(dbpath) as db:
        assert db.execute('SELECT COUNT(*) FROM conversations').fetchone()[0]==0

def test_untrusted_output_cannot_override_prices_or_model():
    profile,intro=validate_turn(ExtractedTurn(**turn(acknowledgement='Confirmed! $1, visit https://bad.example',model='Invented model')))
    assert 'model' not in profile and 'vehicle' not in profile
    assert '$1' not in intro and 'https' not in intro

def test_missing_key_is_explicit(tmp_path, monkeypatch):
    monkeypatch.setenv('LLM_MODE','openai')
    with TestClient(create_app(tmp_path/'missing.db')) as client:
        assert client.get('/status').json()['configured'] is False
        assert client.post('/leads',json={'message':'Hi'}).status_code==503

def test_request_budget(monkeypatch):
    from llm import LLMUnavailable
    import time
    monkeypatch.setenv('OPENAI_API_KEY','test-placeholder-not-a-real-key')
    adapter=OpenAIConversation()
    adapter._calls.extend([time.monotonic()]*60)
    with pytest.raises(LLMUnavailable,match='limit'):
        adapter.respond('hi',{},[],None)
