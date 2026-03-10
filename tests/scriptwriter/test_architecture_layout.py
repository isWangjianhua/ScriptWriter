import importlib


def test_consolidated_project_modules_are_importable():
    projects_memory = importlib.import_module("scriptwriter.projects.memory")
    projects_workflow = importlib.import_module("scriptwriter.projects.workflow")
    projects_store = importlib.import_module("scriptwriter.projects.store")
    knowledge_service = importlib.import_module("scriptwriter.knowledge.service")

    assert hasattr(projects_memory, "MemoryService")
    assert hasattr(projects_workflow, "advance_workflow")
    assert hasattr(projects_store, "InMemoryProjectStore")
    assert hasattr(knowledge_service, "ingest_knowledge_document")


def test_main_exports_project_centric_api_app():
    main_module = importlib.import_module("scriptwriter.main")
    api_module = importlib.import_module("scriptwriter.api.app")

    assert main_module.app is api_module.app
