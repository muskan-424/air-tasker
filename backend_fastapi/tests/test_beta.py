def test_beta_config_endpoint(client):
    response = client.get("/api/beta/config")
    assert response.status_code == 200
    body = response.json()
    assert body["beta_enabled"] is True
    assert "electrical" in body["categories"]
    assert "248001" in body["pin_codes"]
    assert any(lang["code"] == "hi" for lang in body["languages"])
    assert body["feature_flags"]["ai_chat"] is True
