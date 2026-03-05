from fastapi import FastAPI

from scriptwriter.gateway.routers.artifacts import router as artifacts_router
from scriptwriter.gateway.routers.chat import router
from scriptwriter.gateway.routers.uploads import router as uploads_router

app = FastAPI(title="Auto-Screenwriter API")

app.include_router(router)
app.include_router(uploads_router)
app.include_router(artifacts_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("scriptwriter.gateway.app:app", host="0.0.0.0", port=8000, reload=True)
