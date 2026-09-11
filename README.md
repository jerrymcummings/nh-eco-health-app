## Run the FastAPI service

From the repository root:

TODO - handle OPENAI_API_KEY better

```bash
OPENAI_API_KEY="<openai api key here>" uv run uvicorn main:app --app-dir src/nh_eco_health_app --reload
```

Check that the service is reachable at <http://127.0.0.1:8000/health> or open the
interactive API documentation at <http://127.0.0.1:8000/docs>.

The query endpoint requires `OPENAI_API_KEY` and accepts `POST /api/query` with a
JSON body such as `{"prompt": "List all counties"}`.

I guess in a different terminal window do

```bash
uv run streamlit run src/nh_eco_health_app/app.py
```