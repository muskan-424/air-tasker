import pytest
from starlette.websockets import WebSocketDisconnect


def test_notifications_ws_requires_token(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/notifications/ws"):
            pass


def test_notifications_ws_rejects_invalid_token(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/notifications/ws?token=bad-token"):
            pass
