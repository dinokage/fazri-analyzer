import pytest
from fastapi.testclient import TestClient

from main import app
from auth.models import UserRole


@pytest.fixture
def client():
    """Create FastAPI test client"""
    return TestClient(app)


class TestPublicEndpoints:
    """Test public endpoints that don't require authentication"""

    def test_health_check_public(self, client):
        """Test health check is publicly accessible"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_root_endpoint_public(self, client):
        """Test root endpoint is publicly accessible"""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "running"

    def test_chat_health_public(self, client):
        """Test chat health endpoint is publicly accessible"""
        response = client.get("/api/v1/chat/health")
        assert response.status_code == 200
        assert "status" in response.json()

    def test_gitlab_health_public(self, client):
        """Test GitLab health endpoint is publicly accessible"""
        response = client.get("/api/v1/gitlab/health")
        assert response.status_code == 200
        assert "status" in response.json()

    def test_anomaly_health_public(self, client):
        """Test anomaly health endpoint is publicly accessible"""
        response = client.get("/api/v1/anomalies/health")
        assert response.status_code == 200
        assert "success" in response.json()

    def test_spatial_health_public(self, client):
        """Test spatial health endpoint is publicly accessible"""
        response = client.get("/api/v1/spatial/health")
        assert response.status_code == 200
        assert "success" in response.json()


class TestEntityEndpoints:
    """Test entity endpoints with authentication and RBAC"""

    def test_list_entities_without_auth(self, client):
        """Test listing entities requires authentication"""
        response = client.get("/api/v1/entities/")
        assert response.status_code == 401

    def test_list_entities_student_denied(self, client, student_token):
        """Test students cannot list all entities (STAFF+ only)"""
        response = client.get(
            "/api/v1/entities/",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 403

    def test_list_entities_staff_allowed(self, client, staff_token):
        """Test staff can list entities"""
        response = client.get(
            "/api/v1/entities/",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        # May be 200 or 500 depending on Neo4j availability, but not 401/403
        assert response.status_code not in [401, 403]

    def test_fuzzy_search_student_denied(self, client, student_token):
        """Test students cannot use fuzzy search (STAFF+ only)"""
        response = client.get(
            "/api/v1/entities/fuzzy-search?name=test",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 403

    def test_fuzzy_search_staff_allowed(self, client, staff_token):
        """Test staff can use fuzzy search"""
        response = client.get(
            "/api/v1/entities/fuzzy-search?name=test",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        # May be 200 or 500 depending on Neo4j, but not 401/403
        assert response.status_code not in [401, 403]


class TestGraphEndpoints:
    """Test graph/timeline endpoints with authentication"""

    def test_timeline_without_auth(self, client):
        """Test timeline endpoint requires authentication"""
        response = client.get("/api/v1/graph/timeline/test-entity")
        assert response.status_code == 401

    def test_timeline_student_denied(self, client, student_token):
        """Test students cannot access timeline (STAFF+ only)"""
        response = client.get(
            "/api/v1/graph/timeline/test-entity",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 403

    def test_timeline_staff_allowed(self, client, staff_token):
        """Test staff can access timeline"""
        response = client.get(
            "/api/v1/graph/timeline/test-entity",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        # May be 200 or 500 depending on Neo4j, but not 401/403
        assert response.status_code not in [401, 403]


class TestAlertEndpoints:
    """Test alert endpoints with authentication and RBAC"""

    def test_get_alerts_without_auth(self, client):
        """Test getting alerts requires authentication"""
        response = client.get("/api/v1/alerts")
        assert response.status_code == 401

    def test_get_alerts_student_denied(self, client, student_token):
        """Test students cannot access alerts (STAFF+ only)"""
        response = client.get(
            "/api/v1/alerts",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 403

    def test_get_alerts_staff_allowed(self, client, staff_token):
        """Test staff can access alerts"""
        response = client.get(
            "/api/v1/alerts",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        # Should work (200) or fail due to DB (500), but not auth error
        assert response.status_code not in [401, 403]

    def test_create_alert_staff_allowed(self, client, staff_token):
        """Test staff can create alerts"""
        alert_data = {
            "title": "Test Alert",
            "description": "Test description",
            "severity": "HIGH",
            "location": {"zone_id": "zone-1", "coordinates": {"lat": 0, "lng": 0}},
            "anomaly_type": "suspicious_activity"
        }

        response = client.post(
            "/api/v1/alerts",
            json=alert_data,
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        # Should work (200/201) or fail due to DB (500), but not auth error
        assert response.status_code not in [401, 403]


class TestDemoEndpoints:
    """Test demo endpoints (SUPER_ADMIN only) - only available when ALERT_SYSTEM_ENABLED=true"""

    def test_demo_endpoint_without_auth(self, client):
        """Test demo endpoints require authentication (if enabled)"""
        response = client.get("/api/v1/demo/scenario")
        # 401 if enabled, 404 if ALERT_SYSTEM_ENABLED is False
        assert response.status_code in [401, 404]

    def test_demo_endpoint_student_denied(self, client, student_token):
        """Test students cannot access demo endpoints (if enabled)"""
        response = client.get(
            "/api/v1/demo/scenario",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        # 403 if enabled, 404 if ALERT_SYSTEM_ENABLED is False
        assert response.status_code in [403, 404]

    def test_demo_endpoint_staff_denied(self, client, staff_token):
        """Test staff cannot access demo endpoints - admin only (if enabled)"""
        response = client.get(
            "/api/v1/demo/scenario",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        # 403 if enabled, 404 if ALERT_SYSTEM_ENABLED is False
        assert response.status_code in [403, 404]

    def test_demo_endpoint_admin_allowed(self, client, admin_token):
        """Test admin can access demo endpoints (if enabled)"""
        response = client.get(
            "/api/v1/demo/scenario",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Should work (200) or fail due to logic (500), or 404 if not enabled
        # But definitely not 401/403 (auth should pass for admin)
        assert response.status_code not in [401, 403]


class TestGitLabEndpoints:
    """Test GitLab endpoints (SUPER_ADMIN only)"""

    def test_gitlab_status_without_auth(self, client):
        """Test GitLab status requires authentication"""
        response = client.get("/api/v1/gitlab/status")
        assert response.status_code == 401

    def test_gitlab_status_student_denied(self, client, student_token):
        """Test students cannot access GitLab endpoints"""
        response = client.get(
            "/api/v1/gitlab/status",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 403

    def test_gitlab_status_staff_denied(self, client, staff_token):
        """Test staff cannot access GitLab endpoints (admin only)"""
        response = client.get(
            "/api/v1/gitlab/status",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code == 403

    def test_gitlab_status_admin_allowed(self, client, admin_token):
        """Test admin can access GitLab endpoints"""
        response = client.get(
            "/api/v1/gitlab/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Should work (200) or fail due to GitLab (500), but not auth error
        assert response.status_code not in [401, 403]


class TestChatEndpoints:
    """Test chat endpoints (all authenticated users)"""

    def test_chat_tools_without_auth(self, client):
        """Test chat tools endpoint requires authentication"""
        response = client.get("/api/v1/chat/tools")
        assert response.status_code == 401

    def test_chat_tools_student_allowed(self, client, student_token):
        """Test students can access chat tools endpoint"""
        response = client.get(
            "/api/v1/chat/tools",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        # Should work or fail due to service, but not auth
        assert response.status_code not in [401, 403]

    def test_chat_message_staff_allowed(self, client, staff_token):
        """Test staff can send chat messages"""
        response = client.post(
            "/api/v1/chat/message",
            headers={"Authorization": f"Bearer {staff_token}"},
            json={"message": "test", "conversation_id": "test-123"}
        )
        # Should work or fail due to service, but not auth
        assert response.status_code not in [401, 403]


class TestInvalidTokens:
    """Test various invalid token scenarios on protected endpoints"""

    def test_expired_token(self, client, expired_token):
        """Test expired token is rejected on protected endpoint"""
        response = client.get(
            "/api/v1/entities/",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401

    def test_invalid_signature(self, client, invalid_signature_token):
        """Test token with invalid signature is rejected on protected endpoint"""
        response = client.get(
            "/api/v1/entities/",
            headers={"Authorization": f"Bearer {invalid_signature_token}"}
        )
        assert response.status_code == 401

    def test_malformed_token(self, client, malformed_token):
        """Test malformed token is rejected on protected endpoint"""
        response = client.get(
            "/api/v1/entities/",
            headers={"Authorization": f"Bearer {malformed_token}"}
        )
        assert response.status_code == 401

    def test_missing_bearer_prefix(self, client, student_token):
        """Test token without Bearer prefix is rejected on protected endpoint"""
        response = client.get(
            "/api/v1/entities/",
            headers={"Authorization": student_token}
        )
        assert response.status_code == 401

    def test_empty_authorization_header(self, client):
        """Test empty authorization header is rejected on protected endpoint"""
        response = client.get(
            "/api/v1/entities/",
            headers={"Authorization": ""}
        )
        assert response.status_code == 401
