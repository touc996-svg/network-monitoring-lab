def test_health_and_empty_summary(client):
    assert client.get("/health").json()["status"] == "healthy"
    assert client.get("/api/v1/summary").json() == {
        "total_targets": 0,
        "up_targets": 0,
        "down_targets": 0,
        "unchecked_targets": 0,
    }


def test_register_tcp_target_and_successful_check(client, monkeypatch):
    class FakeConnection:
        def close(self):
            pass

    monkeypatch.setattr(
        "network_monitor.service.socket.create_connection",
        lambda address, timeout: FakeConnection(),
    )
    created = client.post("/api/v1/targets", json={
        "name": "Local web service",
        "host": "127.0.0.1",
        "check_type": "tcp",
        "port": 18700,
    })
    assert created.status_code == 201
    target_id = created.json()["id"]

    result = client.post(f"/api/v1/targets/{target_id}/check")
    assert result.status_code == 200
    assert result.json()["check"]["status"] == "up"
    assert result.json()["check"]["message"] == "TCP port 18700 is reachable."
    assert client.get("/api/v1/summary").json()["up_targets"] == 1
    assert len(client.get("/api/v1/checks").json()) == 1


def test_failed_check_is_saved_as_down(client, monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr("network_monitor.service.socket.create_connection", fail)
    target = client.post("/api/v1/targets", json={
        "name": "Unavailable test service",
        "host": "127.0.0.1",
        "check_type": "tcp",
        "port": 9,
    }).json()

    result = client.post(f"/api/v1/targets/{target['id']}/check")
    assert result.status_code == 200
    assert result.json()["check"]["status"] == "down"
    assert "connection refused" in result.json()["check"]["message"]
    assert client.get("/api/v1/summary").json()["down_targets"] == 1


def test_invalid_url_and_missing_tcp_port_are_rejected(client):
    invalid_url = client.post("/api/v1/targets", json={
        "name": "Invalid URL",
        "host": "https://example.com",
        "check_type": "tcp",
        "port": 443,
    })
    assert invalid_url.status_code == 422

    missing_port = client.post("/api/v1/targets", json={
        "name": "Missing port",
        "host": "example.com",
        "check_type": "tcp",
    })
    assert missing_port.status_code == 422


def test_dns_target_and_unknown_target(client, monkeypatch):
    fake_records = [
        (None, None, None, None, ("192.0.2.10", 0)),
    ]
    monkeypatch.setattr(
        "network_monitor.service.socket.getaddrinfo",
        lambda *args, **kwargs: fake_records,
    )
    target = client.post("/api/v1/targets", json={
        "name": "Example DNS",
        "host": "example.com",
        "check_type": "dns",
        "port": None,
    }).json()

    result = client.post(f"/api/v1/targets/{target['id']}/check")
    assert result.json()["check"]["status"] == "up"
    assert "192.0.2.10" in result.json()["check"]["message"]
    assert client.post("/api/v1/targets/999/check").status_code == 404
