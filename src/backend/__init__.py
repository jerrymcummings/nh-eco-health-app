import uvicorn


def main() -> None:
    uvicorn.run("nh_eco_health_app.main:app", host="127.0.0.1", port=8000)
