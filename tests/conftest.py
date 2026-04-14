"""Shared test fixtures.

Tests run against the FastAPI test client without a SQL Warehouse connection.
Env vars are set before AND after import to survive .env.local override=True.
"""

import os

os.environ["SQL_WAREHOUSE_ID"] = ""
os.environ["GENIE_SPACE_ID"] = ""
os.environ["MAS_ENDPOINT"] = ""
os.environ["DATABRICKS_CONFIG_PROFILE"] = ""

import pytest
from fastapi.testclient import TestClient

from energy_theft_detection.backend.app import app  # noqa: E402 — triggers config load

os.environ["SQL_WAREHOUSE_ID"] = ""
os.environ["GENIE_SPACE_ID"] = ""
os.environ["MAS_ENDPOINT"] = ""
os.environ["DATABRICKS_CONFIG_PROFILE"] = ""


@pytest.fixture(scope="session")
def client():
    """FastAPI test client — does not require Databricks connectivity."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def base_url():
    return "/api"
