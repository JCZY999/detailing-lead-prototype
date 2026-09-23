"""Local simulated lead-to-booking prototype. No live messaging or AI calls."""
import json
import os
import re
import sqlite3
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ConfigDict
from pricing import BASE, VEHICLES, BRANDS, ALIASES, quote, catalog

ROOT = Path(__file__).parent
SHOP = {
    'name': 'Desert Shine Auto Detailing',
    'hours': 'Monday–Saturday 9 AM–5 PM; Sunday closed (America/Phoenix)',
    'services': BASE,
    'currency': 'USD',
}

class LeadInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = Field(default=None, max_length=64)

class BookingInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    name: str = Field(min_length=1, max_length=100)

def create_app(db_path=None):
    app = FastAPI(title='Desert Shine · Lead prototype')
    database = Path(db_path or os.environ.get('DATABASE_PATH', ROOT / 'data' / 'leads.sqlite3'))
    database.parent.mkdir(parents=True, exist_ok=True)

    def connect():
        conn = sqlite3.connect(database, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY, profile TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY, conversation_id TEXT NOT NULL,
            role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS bookings (
            id TEXT PRIMARY KEY, conversation_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL, details TEXT NOT NULL, created_at TEXT NOT NULL);
        ''')

    def require(db, cid):
        row = db.execute('SELECT * FROM conversations WHERE id=?', (cid,)).fetchone()
        if not row:
            raise HTTPException(404, 'Conversation not found')
        return row

    @app.get('/')
    def home():
        return FileResponse(ROOT / 'index.html')

    @app.get('/shop')
    def shop():
        return {**SHOP, 'pricing': catalog()}

    @app.get('/pricing')
    def pricing():
        return catalog()

    @app.post('/leads')
    def lead(body: LeadInput):
        now = datetime.now(timezone.utc).isoformat()
        cid = body.conversation_id or str(uuid4())
        with connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if body.conversation_id:
                profile = json.loads(require(db, cid)['profile'])
            else:
                profile = {}
                db.execute('INSERT INTO conversations VALUES (?,?,?)', (cid, '{}', now))
            msg = body.message.lower()
            # Deliberately small, deterministic simulator; this is not an LLM.
            if re.search(r'\b(full|both)\b', msg):
                profile['service'] = 'full'
            else:
                for service in ('interior', 'exterior'):
                    if re.search(r'\b' + service + r'\b', msg):
                        profile['service'] = service
                        break
            for day in ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'):
                if re.search(r'\b' + day + r'\b', msg):
                    profile['day'] = day
                    break
            vehicle = re.search(r'\b(' + '|'.join(VEHICLES) + r')\b', msg)
            if vehicle:
                profile['vehicle'] = vehicle.group(1)
            brand_names = {**{b.lower(): b for b in BRANDS}, **ALIASES}
            for name in sorted(brand_names, key=len, reverse=True):
                if re.search(r'\b' + re.escape(name) + r'\b', msg):
                    profile['brand'] = brand_names[name]
                    break
            if re.search(r'\b(other brand|unlisted brand|unknown brand)\b', msg):
                profile['brand'] = 'Other'
            if 'weekend' in msg:
                profile['weekend_requested'] = True
            missing = [key for key in ('service', 'vehicle', 'brand', 'day') if key not in profile]
            price = quote(profile)
            profile['quote'] = price
            qualified = not missing and profile.get('day') != 'sunday' and price is not None
            url = f'/book/{cid}'
            parts = []
            if profile.get('service'):
                service = profile['service']
                if price:
                    parts.append(f"Your {profile['brand']} {profile['vehicle']} {service} detail is ${price['total_usd']} (base ${price['base_usd']} + vehicle ${price['vehicle_adjustment_usd']} + brand ${price['brand_adjustment_usd']}). Fictional demo price, including tax.")
                else:
                    parts.append(f"Our {service} detail starts at ${BASE[service]}; your vehicle type and brand determine the demo quote.")
            else:
                parts.append('Demo prices start at: interior $149, exterior $89, full $219. Which service would you like?')
            parts.append(SHOP['hours'] + '.')
            if 'vehicle' in missing:
                parts.append('What type of vehicle do you have: ' + ', '.join(VEHICLES) + '?')
            if 'brand' in missing:
                parts.append('What brand is your car? For example Toyota, Honda, BMW, Tesla, or Porsche. See the pricing explorer for all supported brands; use "other brand" if unlisted.')
            elif profile['brand'] not in BRANDS:
                parts.append('Your brand needs a manual quote. Automated test booking is unavailable for unlisted brands.')
            if profile.get('day') == 'sunday':
                parts.append('We are closed Sunday. Would Saturday or a weekday work?')
            elif 'day' in missing:
                parts.append('Would Saturday work for your weekend detail?' if profile.get('weekend_requested') else 'Which day works for you?')
            if qualified:
                parts.append(f"Thanks! I have a {profile['vehicle']} for {profile['service']} detailing on {profile['day'].title()}.")
            parts.append(f'Test booking link: {url}. This demo does not reserve a real appointment.')
            response = ' '.join(parts)
            db.execute('UPDATE conversations SET profile=? WHERE id=?', (json.dumps(profile), cid))
            db.executemany('INSERT INTO messages (conversation_id,role,content,created_at) VALUES (?,?,?,?)',
                           [(cid, 'user', body.message, now), (cid, 'assistant', response, now)])
        return {'conversation_id': cid, 'reply': response, 'profile': profile,
                'qualified': qualified, 'booking_url': url, 'mode': 'simulator'}

    @app.get('/conversations/{cid}')
    def conversation(cid: str):
        with connect() as db:
            row = require(db, cid)
            messages = [dict(r) for r in db.execute('SELECT role,content,created_at FROM messages WHERE conversation_id=? ORDER BY id', (cid,))]
            booking = db.execute('SELECT * FROM bookings WHERE conversation_id=?', (cid,)).fetchone()
        profile = json.loads(row['profile'])
        profile['quote'] = quote(profile)
        return {'id': cid, 'profile': profile, 'messages': messages,
                'booking': dict(booking) if booking else None}

    @app.get('/book/{cid}')
    def booking_page(cid: str):
        with connect() as db:
            require(db, cid)
        return FileResponse(ROOT / 'booking.html')

    @app.post('/book/{cid}')
    def book(cid: str, body: BookingInput):
        with connect() as db:
            db.execute('BEGIN IMMEDIATE')
            profile = json.loads(require(db, cid)['profile'])
            prior = db.execute('SELECT * FROM bookings WHERE conversation_id=?', (cid,)).fetchone()
            if prior:
                return {'booking_id': prior['id'], 'status': 'test_booking_saved', 'simulated': True}
            price = quote(profile)
            if not price or not profile.get('day') or profile['day'] == 'sunday':
                raise HTTPException(409, 'Finish qualification before booking: service, vehicle type, supported brand, and an open day.')
            bid = str(uuid4())
            profile['quote'] = price
            profile['price_usd'] = price['total_usd']
            db.execute('INSERT INTO bookings VALUES (?,?,?,?,?)',
                       (bid, cid, body.name, json.dumps(profile), datetime.now(timezone.utc).isoformat()))
        return {'booking_id': bid, 'status': 'test_booking_saved', 'simulated': True}

    return app

app = create_app()
