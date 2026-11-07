import pytest
from fastapi.testclient import TestClient

from network_monitor.database import initialize_database
from network_monitor.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("NETWORK_MONITOR_DB_PATH", str(tmp_path / "test.db"))
    with TestClient(app) as test_client:
        yield test_client
