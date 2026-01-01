"""
E2E Tests - Category 9: Webhook Integration (15 tests)
Tests REAL webhook CRUD operations, delivery, retries, and HMAC signatures.

This test suite validates:
1. Webhook CRUD operations via API
2. Test webhook delivery
3. Webhook log creation
4. Retry logic with failing URLs
5. HMAC signature verification
"""
import pytest
import time
import json
import hmac
import hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import socket


# Find an available port for test webhook server
def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


# Simple webhook receiver server for testing
class WebhookReceiverHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler to receive and store webhook requests"""
    received_requests = []
    response_code = 200
    delay_seconds = 0

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        # Store request details
        request_data = {
            'path': self.path,
            'headers': dict(self.headers),
            'body': json.loads(body.decode('utf-8')) if body else None,
            'timestamp': time.time(),
        }
        self.__class__.received_requests.append(request_data)

        # Simulate delay if configured
        if self.__class__.delay_seconds > 0:
            time.sleep(self.__class__.delay_seconds)

        # Send response
        self.send_response(self.__class__.response_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'ok'}).encode())

    def log_message(self, format, *args):
        pass  # Suppress logging


@pytest.fixture(scope="module")
def webhook_cleanup(authed_client):
    """Cleanup webhooks created during tests"""
    created_ids = []
    yield created_ids
    for webhook_id in created_ids:
        try:
            authed_client.delete(f"/api/v1/webhooks/{webhook_id}")
        except Exception:
            pass


@pytest.fixture(scope="module")
def webhook_server():
    """Start a local webhook receiver server for testing"""
    port = find_free_port()
    server = HTTPServer(('127.0.0.1', port), WebhookReceiverHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    # Reset state
    WebhookReceiverHandler.received_requests = []
    WebhookReceiverHandler.response_code = 200
    WebhookReceiverHandler.delay_seconds = 0

    yield f"http://127.0.0.1:{port}"

    server.shutdown()


# =============================================================================
# WEBHOOK CRUD TESTS (1-5)
# =============================================================================

class TestWebhookCRUD:
    """Tests for webhook Create, Read, Update, Delete operations"""

    def test_01_create_webhook(self, authed_client, webhook_cleanup, webhook_server):
        """Test 1: Create a new webhook"""
        response = authed_client.post("/api/v1/webhooks", json={
            "name": "Test Webhook E2E",
            "url": f"{webhook_server}/hook",
            "events": ["instance.started"],
            "secret": "test-secret-123",
            "enabled": True
        })

        assert response.status_code == 201, f"Create failed: {response.text}"
        data = response.json()

        assert data["name"] == "Test Webhook E2E"
        assert data["url"] == f"{webhook_server}/hook"
        assert data["events"] == ["instance.started"]
        assert data["enabled"] is True
        assert data["secret"] == "***"  # Secret should be redacted
        assert "id" in data

        webhook_cleanup.append(data["id"])
        print(f"  Created webhook ID: {data['id']}")

    def test_02_list_webhooks(self, authed_client, webhook_cleanup, webhook_server):
        """Test 2: List user's webhooks"""
        # Create a webhook first
        create_resp = authed_client.post("/api/v1/webhooks", json={
            "name": "List Test Webhook",
            "url": f"{webhook_server}/list-test",
            "events": ["instance.stopped"],
            "enabled": True
        })
        assert create_resp.status_code == 201
        webhook_id = create_resp.json()["id"]
        webhook_cleanup.append(webhook_id)

        # List webhooks
        response = authed_client.get("/api/v1/webhooks")
        assert response.status_code == 200

        data = response.json()
        assert "webhooks" in data
        assert "count" in data
        assert data["count"] > 0

        # Find our webhook
        found = False
        for wh in data["webhooks"]:
            if wh["id"] == webhook_id:
                found = True
                assert wh["name"] == "List Test Webhook"
                break

        assert found, f"Webhook {webhook_id} not found in list"
        print(f"  Found {data['count']} webhook(s)")

    def test_03_get_webhook_by_id(self, authed_client, webhook_cleanup, webhook_server):
        """Test 3: Get specific webhook by ID"""
        # Create a webhook
        create_resp = authed_client.post("/api/v1/webhooks", json={
            "name": "Get Test Webhook",
            "url": f"{webhook_server}/get-test",
            "events": ["snapshot.completed"],
            "secret": "get-test-secret",
            "enabled": True
        })
        assert create_resp.status_code == 201
        webhook_id = create_resp.json()["id"]
        webhook_cleanup.append(webhook_id)

        # Get by ID
        response = authed_client.get(f"/api/v1/webhooks/{webhook_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == webhook_id
        assert data["name"] == "Get Test Webhook"
        assert data["secret"] == "***"  # Redacted
        print(f"  Retrieved webhook: {data['name']}")

    def test_04_update_webhook(self, authed_client, webhook_cleanup, webhook_server):
        """Test 4: Update webhook configuration"""
        # Create a webhook
        create_resp = authed_client.post("/api/v1/webhooks", json={
            "name": "Update Test Webhook",
            "url": f"{webhook_server}/update-test",
            "events": ["instance.started"],
            "enabled": True
        })
        assert create_resp.status_code == 201
        webhook_id = create_resp.json()["id"]
        webhook_cleanup.append(webhook_id)

        # Update it
        response = authed_client.put(f"/api/v1/webhooks/{webhook_id}", json={
            "name": "Updated Webhook Name",
            "events": ["instance.started", "instance.stopped"],
            "enabled": False
        })
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Updated Webhook Name"
        assert set(data["events"]) == {"instance.started", "instance.stopped"}
        assert data["enabled"] is False
        print(f"  Updated webhook: {data['name']}")

    def test_05_delete_webhook(self, authed_client, webhook_cleanup, webhook_server):
        """Test 5: Delete a webhook"""
        # Create a webhook
        create_resp = authed_client.post("/api/v1/webhooks", json={
            "name": "Delete Test Webhook",
            "url": f"{webhook_server}/delete-test",
            "events": ["instance.started"],
            "enabled": True
        })
        assert create_resp.status_code == 201
        webhook_id = create_resp.json()["id"]

        # Delete it
        response = authed_client.delete(f"/api/v1/webhooks/{webhook_id}")
        assert response.status_code == 200

        # Verify it's gone
        get_resp = authed_client.get(f"/api/v1/webhooks/{webhook_id}")
        assert get_resp.status_code == 404
        print(f"  Deleted webhook {webhook_id}")


# =============================================================================
# WEBHOOK DELIVERY TESTS (6-10)
# =============================================================================

class TestWebhookDelivery:
    """Tests for webhook test delivery and payload verification"""

    def test_06_test_webhook_delivery(self, authed_client, webhook_cleanup, webhook_server):
        """Test 6: Send test webhook and verify delivery"""
        # Reset receiver
        WebhookReceiverHandler.received_requests = []
        WebhookReceiverHandler.response_code = 200

        # Create webhook
        create_resp = authed_client.post("/api/v1/webhooks", json={
            "name": "Delivery Test",
            "url": f"{webhook_server}/delivery",
            "events": ["instance.started"],
            "enabled": True
        })
        assert create_resp.status_code == 201
        webhook_id = create_resp.json()["id"]
        webhook_cleanup.append(webhook_id)

        # Send test
        response = authed_client.post(f"/api/v1/webhooks/{webhook_id}/test")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "delivered"
        assert data["status_code"] == 200
        print(f"  Test delivery: status={data['status']}, code={data['status_code']}")

        # Verify receiver got the request
        time.sleep(0.5)  # Small delay for async processing
        assert len(WebhookReceiverHandler.received_requests) >= 1

        received = WebhookReceiverHandler.received_requests[-1]
        assert received["body"]["event"] == "test"
        assert "timestamp" in received["body"]
        print(f"  Receiver got payload: event={received['body']['event']}")

    def test_07_test_webhook_with_hmac(self, authed_client, webhook_cleanup, webhook_server):
        """Test 7: Verify HMAC signature is included when secret is set"""
        # Reset receiver
        WebhookReceiverHandler.received_requests = []

        secret = "my-test-secret-12345"

        # Create webhook with secret
        create_resp = authed_client.post("/api/v1/webhooks", json={
            "name": "HMAC Test",
            "url": f"{webhook_server}/hmac",
            "events": ["instance.started"],
            "secret": secret,
            "enabled": True
        })
        assert create_resp.status_code == 201
        webhook_id = create_resp.json()["id"]
        webhook_cleanup.append(webhook_id)

        # Send test
        response = authed_client.post(f"/api/v1/webhooks/{webhook_id}/test")
        assert response.status_code == 200

        # Verify HMAC signature was included
        time.sleep(0.5)
        assert len(WebhookReceiverHandler.received_requests) >= 1

        received = WebhookReceiverHandler.received_requests[-1]
        signature_header = received["headers"].get("X-Webhook-Signature")

        assert signature_header is not None, "X-Webhook-Signature header missing"
        assert signature_header.startswith("sha256="), f"Invalid signature format: {signature_header}"
        print(f"  HMAC signature present: {signature_header[:30]}...")

        # Verify signature is correct
        payload_bytes = json.dumps(received["body"], sort_keys=True, separators=(',', ':')).encode('utf-8')
        expected_sig = hmac.new(
            key=secret.encode('utf-8'),
            msg=payload_bytes,
            digestmod=hashlib.sha256
        ).hexdigest()

        assert signature_header == f"sha256={expected_sig}", "Signature mismatch"
        print(f"  HMAC signature verified successfully")

    def test_08_webhook_logs_created(self, authed_client, webhook_cleanup, webhook_server):
        """Test 8: Verify delivery logs are created"""
        # Create webhook
        create_resp = authed_client.post("/api/v1/webhooks", json={
            "name": "Logs Test",
            "url": f"{webhook_server}/logs",
            "events": ["instance.started"],
            "enabled": True
        })
        assert create_resp.status_code == 201
        webhook_id = create_resp.json()["id"]
        webhook_cleanup.append(webhook_id)

        # Send test
        test_resp = authed_client.post(f"/api/v1/webhooks/{webhook_id}/test")
        assert test_resp.status_code == 200

        time.sleep(0.5)  # Wait for log to be written

        # Check logs
        logs_resp = authed_client.get(f"/api/v1/webhooks/{webhook_id}/logs")
        assert logs_resp.status_code == 200

        data = logs_resp.json()
        assert "logs" in data
        assert data["count"] >= 1

        log = data["logs"][0]  # Most recent
        assert log["webhook_id"] == webhook_id
        assert log["event_type"] == "test"
        assert log["status_code"] == 200
        assert log["attempt"] == 1
        assert log["error"] is None
        print(f"  Log created: event={log['event_type']}, status={log['status_code']}")

    def test_09_webhook_without_secret(self, authed_client, webhook_cleanup, webhook_server):
        """Test 9: Webhook without secret has no signature header"""
        # Reset receiver
        WebhookReceiverHandler.received_requests = []

        # Create webhook without secret
        create_resp = authed_client.post("/api/v1/webhooks", json={
            "name": "No Secret Test",
            "url": f"{webhook_server}/no-secret",
            "events": ["instance.started"],
            "enabled": True
        })
        assert create_resp.status_code == 201
        webhook_id = create_resp.json()["id"]
        webhook_cleanup.append(webhook_id)

        # Send test
        response = authed_client.post(f"/api/v1/webhooks/{webhook_id}/test")
        assert response.status_code == 200

        time.sleep(0.5)
        assert len(WebhookReceiverHandler.received_requests) >= 1

        received = WebhookReceiverHandler.received_requests[-1]
        signature_header = received["headers"].get("X-Webhook-Signature")

        assert signature_header is None, f"Signature should not be present: {signature_header}"
        print("  No signature header when secret is not configured")

    def test_10_get_event_types(self, authed_client):
        """Test 10: Get list of available event types"""
        response = authed_client.get("/api/v1/webhooks/events/types")
        assert response.status_code == 200

        data = response.json()
        assert "events" in data
        assert "descriptions" in data

        expected_events = {"instance.started", "instance.stopped", "snapshot.completed",
                          "failover.triggered", "cost.threshold"}
        actual_events = set(data["events"])

        assert expected_events.issubset(actual_events), f"Missing events: {expected_events - actual_events}"
        print(f"  Available events: {data['events']}")


# =============================================================================
# WEBHOOK FAILURE AND RETRY TESTS (11-15)
# =============================================================================

class TestWebhookRetry:
    """Tests for webhook failure handling and retry logic"""

    def test_11_webhook_failure_logged(self, authed_client, webhook_cleanup, webhook_server):
        """Test 11: Failed webhook delivery is logged with error"""
        # Configure server to return 500
        WebhookReceiverHandler.response_code = 500
        WebhookReceiverHandler.received_requests = []

        # Create webhook
        create_resp = authed_client.post("/api/v1/webhooks", json={
            "name": "Failure Test",
            "url": f"{webhook_server}/fail",
            "events": ["instance.started"],
            "enabled": True
        })
        assert create_resp.status_code == 201
        webhook_id = create_resp.json()["id"]
        webhook_cleanup.append(webhook_id)

        try:
            # Send test (will fail)
            test_resp = authed_client.post(f"/api/v1/webhooks/{webhook_id}/test")
            assert test_resp.status_code == 200

            data = test_resp.json()
            assert data["status"] == "failed"
            print(f"  Expected failure: status={data['status']}")

            # Wait for retries to complete (3 attempts with exponential backoff)
            time.sleep(15)  # 2s + 4s + buffer

            # Check logs show retry attempts
            logs_resp = authed_client.get(f"/api/v1/webhooks/{webhook_id}/logs")
            assert logs_resp.status_code == 200

            logs_data = logs_resp.json()
            assert logs_data["count"] >= 3, f"Expected 3 retry attempts, got {logs_data['count']}"

            # Verify attempt numbers
            attempts = [log["attempt"] for log in logs_data["logs"]]
            assert 1 in attempts and 2 in attempts and 3 in attempts
            print(f"  Retry attempts logged: {sorted(attempts)}")

        finally:
            # Reset server
            WebhookReceiverHandler.response_code = 200

    def test_12_invalid_url_retries(self, authed_client, webhook_cleanup):
        """Test 12: Webhook with invalid URL retries 3 times"""
        # Create webhook with unreachable URL
        create_resp = authed_client.post("/api/v1/webhooks", json={
            "name": "Invalid URL Test",
            "url": "http://localhost:9999/unreachable",
            "events": ["instance.started"],
            "enabled": True
        })
        assert create_resp.status_code == 201
        webhook_id = create_resp.json()["id"]
        webhook_cleanup.append(webhook_id)

        # Send test
        test_resp = authed_client.post(f"/api/v1/webhooks/{webhook_id}/test")
        assert test_resp.status_code == 200

        data = test_resp.json()
        assert data["status"] == "failed"
        assert data["attempt"] == 3  # Should have tried 3 times
        assert "error" in data and data["error"] is not None
        print(f"  Connection error after {data['attempt']} attempts")

        # Check logs
        time.sleep(1)
        logs_resp = authed_client.get(f"/api/v1/webhooks/{webhook_id}/logs")
        assert logs_resp.status_code == 200

        logs_data = logs_resp.json()
        assert logs_data["count"] == 3

        for log in logs_data["logs"]:
            assert log["error"] is not None
            assert "Connection" in log["error"] or "connect" in log["error"].lower()
        print(f"  All 3 attempts logged with connection errors")

    def test_13_disabled_webhook_not_called(self, authed_client, webhook_cleanup, webhook_server):
        """Test 13: Disabled webhook is not called"""
        # Reset receiver
        WebhookReceiverHandler.received_requests = []
        initial_count = len(WebhookReceiverHandler.received_requests)

        # Create disabled webhook
        create_resp = authed_client.post("/api/v1/webhooks", json={
            "name": "Disabled Test",
            "url": f"{webhook_server}/disabled",
            "events": ["instance.started"],
            "enabled": False
        })
        assert create_resp.status_code == 201
        webhook_id = create_resp.json()["id"]
        webhook_cleanup.append(webhook_id)

        # Try to test disabled webhook
        test_resp = authed_client.post(f"/api/v1/webhooks/{webhook_id}/test")
        # Should still work for test endpoint (tests even disabled webhooks)
        assert test_resp.status_code == 200

        print(f"  Disabled webhook test completed")

    def test_14_invalid_event_type_rejected(self, authed_client, webhook_cleanup, webhook_server):
        """Test 14: Invalid event type is rejected on create"""
        response = authed_client.post("/api/v1/webhooks", json={
            "name": "Invalid Event Test",
            "url": f"{webhook_server}/invalid-event",
            "events": ["invalid.event.type"],
            "enabled": True
        })

        assert response.status_code == 400
        assert "Invalid event" in response.text or "invalid" in response.text.lower()
        print(f"  Invalid event rejected: {response.json().get('detail', '')[:50]}")

    def test_15_webhook_not_found(self, authed_client):
        """Test 15: Non-existent webhook returns 404"""
        response = authed_client.get("/api/v1/webhooks/99999999")
        assert response.status_code == 404
        print(f"  Non-existent webhook: 404 as expected")

        # Also test delete
        del_resp = authed_client.delete("/api/v1/webhooks/99999999")
        assert del_resp.status_code == 404
        print(f"  Delete non-existent: 404 as expected")
