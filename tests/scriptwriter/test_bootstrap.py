import importlib


def test_app_module_importable():
    module = importlib.import_module("scriptwriter.main")
    assert hasattr(module, "app")
