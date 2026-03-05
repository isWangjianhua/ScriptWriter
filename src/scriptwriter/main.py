
from scriptwriter.gateway.app import app

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("scriptwriter.gateway.app:app", host="0.0.0.0", port=8000, reload=True)
