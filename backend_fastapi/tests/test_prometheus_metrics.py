def test_prometheus_metrics_endpoint(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.text
    assert "vayutask_http_requests_total" in body
    assert "text/plain" in (response.headers.get("content-type") or "")


def test_prometheus_metrics_after_request(client):
    client.get("/api/health")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "vayutask_http_requests_total" in response.text
