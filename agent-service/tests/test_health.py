from fastapi.testclient import TestClient


def test_health_sin_nest_responde_degraded(client: TestClient, fake_nest_down) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "degraded", "agent": True, "nest": False}


def test_health_con_nest_responde_ready(client_nest_up: TestClient) -> None:
    response = client_nest_up.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "agent": True, "nest": True}


def test_health_alias_en_la_raiz(client_nest_up: TestClient) -> None:
    response = client_nest_up.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "agent": True, "nest": True}
