# Detailing lead-to-booking prototype

A local FastAPI app with `POST /leads`, a browser conversation lab, a working test booking page, and SQLite storage. The fictional Desert Shine shop offers interior ($149), exterior ($89), and full detailing ($219), Monday–Saturday 9 AM–5 PM in Phoenix time. Sunday is closed.

## Run (Python 3.10+)

From this folder on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. Interactive API docs are at `/docs`.

## Try the complete flow

1. Send: `Hi, I want an interior detail this weekend.`
2. The assistant quotes $149, provides shop hours, asks for vehicle type and Saturday, and returns a test booking link.
3. Reply: `My SUV. Saturday works.`
4. Open the test booking link, enter a fictional name, and save.
5. Refresh the conversation page: messages persist. Inspect `/conversations/{conversation_id}` for the transcript and booking.

API request:

```json
{"message":"I want an interior detail this weekend."}
```

Send later messages to `POST /leads` with the returned `conversation_id`. `booking_url` is a same-origin relative URL. `POST /book/{conversation_id}` accepts `{"name":"Alex"}`. Duplicate submissions return the original test booking. Unqualified leads cannot book.

## Storage and tests

SQLite creates `data/leads.sqlite3` automatically. Set `DATABASE_PATH` to override it. Every successful lead request saves both messages and its qualification state in one transaction. Test bookings persist separately and allow one booking per conversation.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tests use temporary databases and cover the full conversation, booking-page access, qualification gates, persistence after app recreation, validation, Sunday closure, and concurrent duplicate bookings. Testing follows FastAPI's TestClient approach: https://fastapi.tiangolo.com/tutorial/testing/.

## Prototype boundaries

The assistant is a deterministic simulator, not a live AI model. It recognizes service names, weekdays, and these vehicle types: sedan, SUV, truck, coupe, van, hatchback. It does not interpret arbitrary language, negation, exact dates, or time slots. For predictable testing, use direct affirmative answers as above. No API key is needed.

A test booking records a preferred weekday, not calendar availability or an appointment reservation. There is no SMS integration, payment flow, or external booking service. Conversation IDs act as local access tokens; there is no authentication. Use fictional data and keep the server on localhost. Before a real pilot, add authentication, a genuine AI adapter, calendar availability with dates/time slots, and messaging consent and delivery handling.
