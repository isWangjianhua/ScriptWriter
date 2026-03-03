from fastapi import FastAPI
from scriptwriter.gateway.routers.chat import router

app = FastAPI(title="Auto-Screenwriter API")

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("scriptwriter.gateway.app:app", host="0.0.0.0", port=8000, reload=True)
