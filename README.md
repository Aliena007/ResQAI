# ResQAI
AI-Powered Disaster Response &amp; Coordination Agent

## Local setup

Create the environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set a random `SECRET_KEY`. The agent defaults
to Gemini because its free tier is simple to access and requires no extra SDK;
the application still works without a key by using its keyword fallback. For a
fully local option, install Ollama and set `RESQAI_LLM_PROVIDER=ollama`.

Start the app with:

```powershell
.\.venv\Scripts\python.exe run.py
```

The minimal auth API is available at `/auth/register`, `/auth/login`, and
`/auth/logout`. Send JSON or form fields named `username`, `email`, and
`password` to register; login accepts either username or email.

After login, submit an incident to `POST /incidents` with a JSON body such as
`{"description":"Flood blocks the main road","location":"Central Road"}`.
The response includes the AI or fallback `category`, `severity`, `summary`, and
`recommended_action`. Use `GET /incidents` to list reports, or
`GET /incidents/<id>` for one report. `GET /health` is available for a basic
startup check. Incident status can be changed with `PATCH /incidents/<id>` and
one of `reported`, `acknowledged`, `in_progress`, or `resolved`.

The main preventive feature is the **ResQAI Preventive Weather Agent** in the
browser dashboard. Enter a city or geographical location and it uses the free
Open-Meteo geocoding and forecast models to analyze five days of rain,
thunderstorm, snow, and wind signals. It returns a risk level, the highest-risk
day, transparent reasoning, and preparation actions before an incident happens.
This workflow needs no API key. It is a forecast risk assistant, not a guarantee
of safety; confirm high-risk results with official local warnings.

## Development and deployment

Run the tests with:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

For production, set `FLASK_ENV=production`, a strong `SECRET_KEY`, and a
production WSGI server such as Waitress or Gunicorn. Do not use Flask's debug
server in production. SQLite is suitable for local learning; use a managed
PostgreSQL database when multiple responders need concurrent access.
