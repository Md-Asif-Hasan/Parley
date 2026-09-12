import pytest
from fastapi.testclient import TestClient
from app.main import app, state_manager

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

def test_state_endpoint():
    response = client.get("/api/state")
    assert response.status_code == 200
    data = response.json()
    assert "transcript" in data
    assert "speakers" in data

def test_websocket_connect_and_rename():
    state_manager.reset()
    with client.websocket_connect("/ws/meeting") as websocket:
        init_data = websocket.receive_json()
        assert init_data["type"] == "state.init"

        status_data = websocket.receive_json()
        assert status_data["type"] == "status"

        # Test rename
        websocket.send_json({
            "type": "speaker.rename",
            "data": {"speaker_id": "speaker_0", "name": "Alice"}
        })

        rename_event = websocket.receive_json()
        assert rename_event["type"] == "speaker.updated"
        assert rename_event["data"]["speakers"]["speaker_0"] == "Alice"
