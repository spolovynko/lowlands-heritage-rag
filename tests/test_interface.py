from fastapi.testclient import TestClient

from lowlands_lens.api.app import create_app


def test_interface_and_separate_assets_are_served() -> None:
    client = TestClient(create_app())

    page = client.get("/")
    styles = client.get("/static/styles.css")
    script = client.get("/static/app.js")

    assert page.status_code == 200
    assert page.headers["content-type"].startswith("text/html")
    assert styles.status_code == 200
    assert styles.headers["content-type"].startswith("text/css")
    assert script.status_code == 200
    assert "javascript" in script.headers["content-type"]
    assert '<link rel="stylesheet" href="/static/styles.css"' in page.text
    assert '<script src="/static/app.js"' in page.text


def test_interface_exposes_required_phase_2_states_and_boundaries() -> None:
    client = TestClient(create_app())

    page = client.get("/").text
    script = client.get("/static/app.js").text

    for visible_state in (
        "Results",
        "Empty",
        "Service error",
        "Answered",
        "Abstention",
        "Generation unavailable",
    ):
        assert visible_state in page

    assert "synthetic prototype" in page
    assert "No Europeana access" in page
    assert 'const API_PREFIX = "/api/v1"' in script
    assert "fetch(`${API_PREFIX}/search`" in script
    assert "fetch(`${API_PREFIX}/answer`" in script
    assert "innerHTML" not in script


def test_interface_loads_no_external_runtime_assets() -> None:
    client = TestClient(create_app())

    page = client.get("/").text
    styles = client.get("/static/styles.css").text
    script = client.get("/static/app.js").text

    assert "https://" not in page
    assert "https://" not in styles
    assert "https://" not in script
