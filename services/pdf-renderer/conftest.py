import sys
from types import ModuleType
from unittest.mock import MagicMock

if "playwright.async_api" not in sys.modules:
    stub = ModuleType("playwright.async_api")
    stub.async_playwright = MagicMock()
    sys.modules["playwright"] = ModuleType("playwright")
    sys.modules["playwright.async_api"] = stub

if "googleapiclient.http" not in sys.modules:
    googleapiclient_stub = ModuleType("googleapiclient")
    http_stub = ModuleType("googleapiclient.http")
    http_stub.MediaIoBaseUpload = MagicMock()
    sys.modules["googleapiclient"] = googleapiclient_stub
    sys.modules["googleapiclient.http"] = http_stub
