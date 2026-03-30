from bs4 import BeautifulSoup


def _get_csrf(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    field = soup.find("input", {"name": "csrf_token"})
    assert field is not None
    return field["value"]


def test_admin_dashboard_requires_session(client):
    response = client.get("/admin")
    assert response.status_code == 401


def test_admin_login_and_dashboard(client):
    login_page = client.get("/admin/login")
    csrf_token = _get_csrf(login_page.text)
    response = client.post(
        "/admin/login",
        data={"api_key": "test-admin-key", "csrf_token": csrf_token},
        follow_redirects=False,
    )
    assert response.status_code == 303
    dashboard = client.get("/admin")
    assert dashboard.status_code == 200
    assert "Admin Metrics" in dashboard.text


def test_public_page_does_not_expose_admin_key(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "change-me" not in response.text
    assert "/admin?key=" not in response.text


def test_submit_validation_returns_html(client):
    page = client.get("/")
    csrf_token = _get_csrf(page.text)
    response = client.post(
        "/submit",
        data={
            "user_name": "Aaron",
            "role": "analyst",
            "prompt": "hi",
            "evidence_strength": 0.9,
            "sensitivity": "low",
            "requested_action": "",
            "csrf_token": csrf_token,
        },
    )
    assert response.status_code == 422
    assert "Form Error" in response.text
