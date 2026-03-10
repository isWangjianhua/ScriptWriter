from scriptwriter.api.app import app

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("scriptwriter.api.app:app", host="0.0.0.0", port=8000, reload=True)
