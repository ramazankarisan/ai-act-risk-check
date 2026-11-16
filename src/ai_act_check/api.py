"""HTTP API for AI Act Risk Check."""

from fastapi import FastAPI

app = FastAPI(title="AI Act Risk Check")


@app.get("/health")
def health() -> dict[str, str]:
    """Return a liveness signal for monitoring and container probes."""
    return {"status": "ok"}
