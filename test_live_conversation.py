"""Opt-in real-provider smoke test; performs four billable model requests.

Set RUN_LIVE_LLM=1 and optionally DEMO_URL, then:
python -m pytest test_live_conversation.py -q -s
Never use real customer details. This test leaves a fictional test booking.
"""
import os
import json
import httpx
import pytest

@pytest.mark.skipif(os.getenv('RUN_LIVE_LLM') != '1', reason='Live API use requires explicit opt-in')
def test_real_conversation():
    base=os.getenv('DEMO_URL','https://detailing-lead-prototype.onrender.com').rstrip('/')
    with httpx.Client(base_url=base, timeout=60) as client:
        status=client.get('/status').raise_for_status().json()
        assert status['mode']=='openai' and status['configured'], 'Configure OPENAI_API_KEY before testing'
        cid=None
        prompts=[
            'My BMW X5 seats are messy after a road trip. I need the inside cleaned this weekend.',
            'Sunday works best for me.',
            'Okay, Saturday instead.',
            'Actually, skip the inside. I only want the outside cleaned. Keep Saturday.',
        ]
        for index,message in enumerate(prompts):
            result=client.post('/leads',json={'message':message,'conversation_id':cid}).raise_for_status().json()
            assert result['mode']=='openai'
            cid=result['conversation_id']
            print('\nCustomer:',message,'\nAssistant:',result['reply'])
            if index==0:
                assert result['profile']['service']=='interior'
                assert result['profile']['model']=='X5'
                assert result['profile']['quote']['total_usd']==204
            elif index==1:
                assert not result['qualified']
                assert client.post(result['booking_url'],json={'name':'Alex Demo'}).status_code==409
            elif index==2:
                assert result['qualified'] and result['profile']['day']=='saturday'
        assert result['profile']['service']=='exterior'
        assert result['profile']['quote']['total_usd']==124
        assert result['profile']['day']=='saturday'
        assert client.get(result['booking_url']).status_code==200
        booking=client.post(result['booking_url'],json={'name':'Alex Demo'}).raise_for_status().json()
        assert booking['simulated']
        saved=client.get('/conversations/'+cid).raise_for_status().json()
        assert len(saved['messages'])==8
        assert json.loads(saved['booking']['details'])['price_usd']==124
