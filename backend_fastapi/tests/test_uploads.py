def test_upload_evidence_file_requires_auth(client):
    response = client.post(
        "/api/uploads/evidence",
        files={"file": ("test.jpg", b"fakejpeg", "image/jpeg")},
    )
    assert response.status_code == 401
