## Run the FastAPI service

From the repository root:

```bash
uv run uvicorn nh_eco_health_app.main:app --reload
```

Check that the service is reachable at <http://127.0.0.1:8000/health> or open the
interactive API documentation at <http://127.0.0.1:8000/docs>.

The query endpoint requires `OPENAI_API_KEY` and accepts `POST /api/query` with a
JSON body such as `{"prompt": "List all counties"}`.
