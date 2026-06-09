import io

from app.main import app
from fastapi.testclient import TestClient


def test_upload_evidence_file_requires_auth():
    with TestClient(app) as client:
        response = client.post(
            "/api/uploads/evidence",
            files={"file": ("test.jpg", io.BytesIO(b"fakejpeg"), "image/jpeg")},
        )
    assert response.status_code == 401


def test_upload_evidence_file_rejects_bad_type():
    with TestClient(app) as client:
        email = "upload_test@example.com"
        client.post("/api/auth/register", json={"email": email, "password": "secret123", "role": "TASKER"})
        login = client.post("/api/auth/login", json={"email": email, "password": "secret123"})
        token = login.json()["access_token"]
        response = client.post(
            "/api/uploads/evidence",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("bad.txt", io.BytesIO(b"hello"), "text/plain")},
        )
    assert response.status_code == 400
