from fastapi.testclient import TestClient

SAMPLE_EVENT = {
    "host": "api.anthropic.com",
    "provider": "anthropic",
    "surface": "api",
    "risk_score": 9,
    "rationale": "Risk 9/10: detected 1 finding(s) (1x credential).",
    "categories": ["credential"],
    "finding_count": 1,
}


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_event(client: TestClient) -> None:
    response = client.post("/events", json=SAMPLE_EVENT)
    assert response.status_code == 201
    body = response.json()
    assert body["host"] == "api.anthropic.com"
    assert body["risk_score"] == 9
    assert "id" in body
    assert "created_at" in body


def test_create_event_rejects_out_of_range_risk_score(client: TestClient) -> None:
    bad_event = {**SAMPLE_EVENT, "risk_score": 11}
    response = client.post("/events", json=bad_event)
    assert response.status_code == 422


def test_list_events_returns_created_events(client: TestClient) -> None:
    client.post("/events", json=SAMPLE_EVENT)
    client.post("/events", json={**SAMPLE_EVENT, "risk_score": 3, "host": "claude.ai"})

    response = client.get("/events")
    assert response.status_code == 200
    events = response.json()
    assert len(events) == 2


def test_list_events_filters_by_min_risk(client: TestClient) -> None:
    client.post("/events", json=SAMPLE_EVENT)  # risk 9
    client.post("/events", json={**SAMPLE_EVENT, "risk_score": 2, "host": "claude.ai"})

    response = client.get("/events", params={"min_risk": 5})
    assert response.status_code == 200
    events = response.json()
    assert len(events) == 1
    assert events[0]["risk_score"] == 9


def test_list_events_orders_newest_first(client: TestClient) -> None:
    client.post("/events", json={**SAMPLE_EVENT, "host": "first.example.com"})
    client.post("/events", json={**SAMPLE_EVENT, "host": "second.example.com"})

    response = client.get("/events")
    events = response.json()
    assert events[0]["host"] == "second.example.com"
