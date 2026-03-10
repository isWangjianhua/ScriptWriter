from fastapi import FastAPI

from scriptwriter.api.routers.projects import router as projects_router
from scriptwriter.knowledge.dependencies import check_knowledge_dependencies

check_knowledge_dependencies()
app = FastAPI(title="ScriptWriter Project API")
app.include_router(projects_router)
