import pytest
from unittest.mock import MagicMock, patch
from codegraphcontext.core.database import DatabaseManager


def test_database_manager_is_singleton():
    a = DatabaseManager()
    b = DatabaseManager()
    assert a is b

def test_get_driver_missing_env_vars(monkeypatch):
    DatabaseManager._instance = None  # reset singleton

    monkeypatch.delenv("NEO4J_URI", raising=False)
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)

    db = DatabaseManager()

    with pytest.raises(ValueError):
        db.get_driver()

def test_close_driver_closes_driver():
    db = DatabaseManager()
    mock_driver = MagicMock()
    db._driver = mock_driver

    db.close_driver()

    mock_driver.close.assert_called_once()
    assert db._driver is None


def test_is_connected_without_driver():
    db = DatabaseManager()
    db._driver = None
    assert db.is_connected() is False


def test_is_connected_session_exception():
    db = DatabaseManager()

    class BadDriver:
        def session(self):
            raise Exception("boom")

    db._driver = BadDriver()
    assert db.is_connected() is False


def test_connection_authentication_error(monkeypatch):
    def fake_driver(*args, **kwargs):
        raise Exception("authentication failed")

    monkeypatch.setattr("neo4j.GraphDatabase.driver", fake_driver)

    ok, err = DatabaseManager.test_connection(
        "neo4j://localhost:7687", "neo4j", "badpass"
    )

    assert ok is False
    assert "authentication" in err.lower()


def test_get_driver_session_run_failure(monkeypatch):
    DatabaseManager._instance = None  # reset singleton

    monkeypatch.setenv("NEO4J_URI", "neo4j://localhost:7687")
    monkeypatch.setenv("NEO4J_USERNAME", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "pass")

    class FakeSession:
        def run(self, *_):
            raise Exception("boom")

        def consume(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class FakeDriver:
        def session(self):
            return FakeSession()

        def close(self):
            pass

    monkeypatch.setattr(
        "neo4j.GraphDatabase.driver",
        lambda *args, **kwargs: FakeDriver()
    )

    db = DatabaseManager()

    with pytest.raises(Exception):
        db.get_driver()

    assert db._driver is None


def test_is_connected_success():
    db = DatabaseManager()

    class GoodSession:
        def run(self, *_):
            return self

        def consume(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class GoodDriver:
        def session(self):
            return GoodSession()

    db._driver = GoodDriver()

    assert db.is_connected() is True
