"""Integration tests for FastAPI endpoints: health, index, search, and history."""

from fastapi.testclient import TestClient

AUTH_HEADERS = {"X-API-Key": "test-secret-key"}


def test_api_health_public(api_client: TestClient):
    resp = api_client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "obsidian-rag"
    assert data["status"] == "online"


def test_api_auth_enforcement(api_client: TestClient):
    # Without header -> 401
    resp = api_client.post("/index", json={})
    assert resp.status_code == 401

    # With wrong key -> 401
    resp = api_client.post("/index", json={}, headers={"X-API-Key": "wrong"})
    assert resp.status_code == 401


def test_api_index_and_search_flow(api_client: TestClient):
    # 1. Trigger index
    idx_resp = api_client.post("/index", json={"full_reindex": True}, headers=AUTH_HEADERS)
    assert idx_resp.status_code == 200
    report = idx_resp.json()["report"]
    assert report["added"] > 0

    # 2. Search endpoint
    search_resp = api_client.post(
        "/search",
        json={"query": "reciprocal rank fusion", "top_k": 3},
        headers=AUTH_HEADERS,
    )
    assert search_resp.status_code == 200
    s_data = search_resp.json()
    assert s_data["count"] > 0
    assert len(s_data["results"]) <= 3

    # 3. History endpoint
    hist_resp = api_client.get("/history", headers=AUTH_HEADERS)
    assert hist_resp.status_code == 200
    assert "history" in hist_resp.json()


def test_api_notes_related(api_client: TestClient):
    # Index first
    api_client.post("/index", json={}, headers=AUTH_HEADERS)

    # Health check gives notes count
    h_data = api_client.get("/").json()
    assert h_data["total_notes"] > 0

    # Query with search to get note_id
    search_resp = api_client.post("/search", json={"query": "architecture", "top_k": 1}, headers=AUTH_HEADERS)
    res = search_resp.json()["results"]
    if res:
        note_id = res[0]["note_id"]
        rel_resp = api_client.get(f"/notes/{note_id}/related", headers=AUTH_HEADERS)
        assert rel_resp.status_code == 200
        assert "related" in rel_resp.json()

