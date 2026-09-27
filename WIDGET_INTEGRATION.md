# AI Growth Engine widget

The website serves a bundled React chat widget on its public pages. Existing prototype forms remain available.

Until configured, the widget displays **Not connected** and cannot send messages or book appointments.

To activate, deploy the AI Growth Engine backend and configure these Render environment variables:

- `AI_GROWTH_ENGINE_API_URL`: public HTTPS backend URL (no credentials/query string).
- `AI_GROWTH_ENGINE_BUSINESS_ID`: the real tenant UUID provisioned by that backend.

Configure that tenant to allow origin `https://detailing-lead-prototype.onrender.com` and load business-approved knowledge. Keep OpenAI and provider secrets on the backend. Confirm bookings only from the real booking provider. The widget never uses the legacy prototype's simulated booking endpoint.

`GET /api/chat-widget/config` exposes only public routing configuration, with caching disabled. Invalid/missing configuration fails closed.
