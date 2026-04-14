import sys
from types import ModuleType
from unittest.mock import MagicMock

if "playwright.async_api" not in sys.modules:
    stub = ModuleType("playwright.async_api")
    stub.async_playwright = MagicMock()
    sys.modules["playwright"] = ModuleType("playwright")
    sys.modules["playwright.async_api"] = stub
