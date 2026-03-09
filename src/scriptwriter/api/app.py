from fastapi import FastAPI

from scriptwriter.api.routers.projects import router as projects_router

app = FastAPI(title="ScriptWriter Project API")
app.include_router(projects_router)
