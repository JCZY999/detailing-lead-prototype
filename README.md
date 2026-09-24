# Detailing lead-to-booking prototype

A local FastAPI app with `POST /leads`, a browser conversation lab, a working test booking page, and SQLite storage. The fictional Desert Shine shop offers interior (from $149), exterior (from $89), and full detailing (from $219), Monday–Saturday 9 AM–5 PM in Phoenix time. Sunday is closed.

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
2. The assistant gives a $149 starting price, provides shop hours, asks for vehicle type, brand, and Saturday, and returns a test booking link.
3. Reply: `My Toyota SUV. Saturday works.`
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

Without an API key, the assistant uses a deterministic simulator. With OPENAI_API_KEY configured, it uses OpenAI for language understanding and a conversational acknowledgement; prices, hours, qualification questions, and booking links are rendered by application code. It recognizes service names, weekdays, and these vehicle types: sedan, SUV, truck, coupe, van, hatchback, wagon, crossover, minivan. It also recognizes the 36 brands in `pricing.py` and aliases such as Chevy, VW, and Mercedes. It does not interpret arbitrary language, negation, exact dates, or time slots. For predictable simulator testing, use direct affirmative answers as above. Simulator mode needs no API key.

A test booking records a preferred weekday, not calendar availability or an appointment reservation. There is no SMS integration, payment flow, or external booking service. Conversation IDs act as local access tokens; there is no authentication. Use fictional data and keep the server on localhost. Before a real pilot, add authentication, calendar availability with dates/time slots, and messaging consent and delivery handling.

## Vehicle and brand pricing

All prices are fictional, tax-inclusive demo data, not market research. `pricing.py` is the single source of truth; `/pricing` exposes the catalog. The browser pricing explorer compares all three services by vehicle and brand. A quote equals the service base + vehicle adjustment + brand-tier adjustment. Brand tiers are arbitrary demo shop rules, not claims about real-world detailing costs.

| Vehicle | Interior add-on | Exterior add-on | Full add-on |
| --- | ---: | ---: | ---: |
| Coupe / sedan / hatchback | $0 | $0 | $0 |
| Wagon | $15 | $10 | $20 |
| Crossover | $20 | $10 | $25 |
| SUV | $35 | $20 | $45 |
| Truck | $25 | $25 | $40 |
| Van | $50 | $30 | $65 |
| Minivan | $45 | $25 | $60 |

Standard brands add $0. Premium brands add $20 / $15 / $30 for interior / exterior / full. Specialty brands add $40 / $30 / $60. Example interior totals: Toyota sedan $149; BMW SUV $204; Porsche SUV $224.

Brand is now required for qualification. Say `other brand` for an unlisted make; this requires a manual quote and blocks automated booking. Existing conversations without a brand must provide one before booking. Existing saved bookings retain their original price snapshot. Changing the service, type, or recognized brand recalculates the quote; after booking, the saved booking remains unchanged. Recognized model names within a known brand determine the default vehicle type. The simulator still requires direct affirmative messages and does not handle negation or multiple vehicles.


## Car models

The catalog in `car_models.py` contains 108 representative models across all 36 brands, including older vehicles. It is not a complete current-year inventory. Body types are demo shop pricing defaults; choose **Other / not listed** for a different trim/body style and select the type manually. No extra model surcharge is added.

The browser model dropdown filters by brand and fills the vehicle type. Changing brands clears the previous model. Quotes, transcripts, and booking details include the selected model. The API accepts an optional `selected_vehicle` object, for example:

```json
{"message":"interior Saturday","selected_vehicle":{"brand":"BMW","model":"X5","vehicle":"suv"}}
```

The server validates the brand/model pair and derives the type from its own catalog. Direct affirmative text such as `Toyota Sienna` takes priority over the dropdown selection. An explicit conflicting type clears the model. Brand-only changes clear a previous model; unlisted models can still be booked by brand and manually selected type. Existing requests without `selected_vehicle` continue to work.

Representative manufacturer references: https://www.toyota.com/all-vehicles/ and https://www.bmwusa.com/vehicles/x-series/x5/bmw-x5.html. This catalog is a demo selection, not a manufacturer-certified database.
## OpenAI conversation mode

1. In Render, open this service's **Environment**, click **Edit**, and add `OPENAI_API_KEY` as a secret. Never paste the key into chat, commit it, or put it in browser JavaScript.
2. Save and redeploy. `LLM_MODE=auto` (default) activates OpenAI when the key exists. Optional `LLM_MODE=openai` requires it and fails explicitly if absent. `LLM_MODE=simulator` forces the old demo.
3. `OPENAI_MODEL` defaults to `gpt-4o-mini`; override with a Responses/Structured Outputs-compatible model your API account can access. API billing/credit is separate from any ChatGPT subscription.
4. `/status` exposes mode, model name, and a configured boolean only. A configured key is not proof it is valid; only a successful live response verifies access.

The server sends the latest message, current profile, selected vehicle, and up to 12 recent messages to OpenAI with `store=false`. No key is returned to the browser. The LLM interprets follow-ups and corrections using strict structured output; server code validates catalog membership and computes prices. The model cannot supply a price or booking URL field or create a booking. Its short acknowledgement is generated text, not a guarantee of service scope. Requests time out, incomplete/refused/malformed responses fail explicitly, and failures do not silently fall back to the simulator or save fabricated replies.

The demo allows 60 model attempts per hour per process and 20 turns per conversation. The process counter resets on restart and is not a billing cap or production abuse protection. Set project spending limits in OpenAI and add authentication before a real pilot. No API key is committed; demo SQLite data still resets on Render restarts.

### Verification

`python -m pytest -q` runs offline tests. `test_llm.py` mocks the provider: these tests verify wiring, history, correction handling, pricing, failures, and booking persistence; they do NOT establish real model quality.

To opt in to the real conversation test (four billable calls and one fictional test booking):

```powershell
$env:RUN_LIVE_LLM = "1"
python -m pytest test_live_conversation.py -q -s
```

The live test checks a BMW X5 interior inquiry, Sunday closure, agreement to Saturday, a correction to exterior-only, the $124 quote, and saved booking/transcript. It refuses to pass in simulator mode. Without a configured working key, this test remains pending.

API implementation reference: https://developers.openai.com/api/docs/guides/structured-outputs