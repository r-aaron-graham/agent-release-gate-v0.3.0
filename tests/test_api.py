def test_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_request_requires_admin_key(client):
    payload = {
        "user_name": "Aaron",
        "role": "analyst",
        "prompt": "Summarize the onboarding checklist for new team members",
        "evidence_strength": 0.9,
        "sensitivity": "low",
    }
    response = client.post("/api/v1/requests", json=payload)
    assert response.status_code == 401


def test_create_request_with_admin_key(client):
    headers = {"Authorization": "Bearer test-admin-key"}
    payload = {
        "user_name": "Aaron",
        "role": "analyst",
        "prompt": "Summarize the onboarding checklist for new team members",
        "evidence_strength": 0.9,
        "sensitivity": "low",
    }
    response = client.post("/api/v1/requests", json=payload, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "approved"


def test_requests_endpoint_requires_admin_key(client):
    response = client.get("/api/v1/requests")
    assert response.status_code == 401


def test_requests_endpoint_is_paginated(client):
    headers = {"Authorization": "Bearer test-admin-key"}
    for idx in range(3):
        client.post(
            "/api/v1/requests",
            headers=headers,
            json={
                "user_name": f"Aaron {idx}",
                "role": "analyst",
                "prompt": f"Summarize onboarding step {idx}",
                "evidence_strength": 0.9,
                "sensitivity": "low",
            },
        )
    response = client.get("/api/v1/requests?limit=2&offset=0", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert body["pagination"]["limit"] == 2
    assert body["pagination"]["total"] == 3


def test_request_lookup_by_id(client):
    headers = {"Authorization": "Bearer test-admin-key"}
    created = client.post(
        "/api/v1/requests",
        headers=headers,
        json={
            "user_name": "Aaron",
            "role": "analyst",
            "prompt": "Summarize onboarding step unique",
            "evidence_strength": 0.9,
            "sensitivity": "low",
        },
    ).json()
    response = client.get(f"/api/v1/requests/{created['request_id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == created["request_id"]
