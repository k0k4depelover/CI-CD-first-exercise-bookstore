"""
Basic tests for BookVault API.
These tests are provided so you can integrate them into CI/CD.
"""

import json
import pytest
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from unittest.mock import patch, MagicMock
from main import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["status"] == "ok"


def test_metrics_endpoint(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert b"bookvault_requests_total" in resp.data


@patch("main.get_db")
def test_list_books(mock_db, client):
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        {"id": 1, "title": "Test Book", "author": "Author", "stock": 5}
    ]
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_db.return_value = mock_conn

    resp = client.get("/api/v1/books")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data) == 1
    assert data[0]["title"] == "Test Book"


@patch("main.get_db")
def test_get_book_not_found(mock_db, client):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_db.return_value = mock_conn

    resp = client.get("/api/v1/books/999")
    assert resp.status_code == 404


@patch("main.get_db")
def test_create_book_missing_fields(mock_db, client):
    resp = client.post("/api/v1/books", json={"genre": "Tech"})
    assert resp.status_code == 400
    data = json.loads(resp.data)
    assert "error" in data


def test_health_has_timestamp(client):
    resp = client.get("/health")
    data = json.loads(resp.data)
    assert "timestamp" in data
