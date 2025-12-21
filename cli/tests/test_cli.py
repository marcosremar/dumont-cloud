"""Tests for Dumont CLI - Auto-discovery mode"""
import pytest
from unittest.mock import patch, MagicMock, Mock
import sys
import os
import json

# Add CLI path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.api_client import APIClient
from commands.base import CommandBuilder
from utils.token_manager import TokenManager


# ============================================================
# Mock OpenAPI Schema for Testing
# ============================================================

MOCK_OPENAPI_SCHEMA = {
    "paths": {
        "/api/auth/login": {
            "post": {"summary": "Login", "requestBody": {}}
        },
        "/api/auth/logout": {
            "post": {"summary": "Logout"}
        },
        "/api/auth/me": {
            "get": {"summary": "Get current user"}
        },
        "/api/auth/register": {
            "post": {"summary": "Register new user", "requestBody": {}}
        },
        "/api/v1/instances": {
            "get": {"summary": "List instances", "parameters": []},
            "post": {"summary": "Create instance", "requestBody": {}}
        },
        "/api/v1/instances/{instance_id}": {
            "get": {"summary": "Get instance", "parameters": []},
            "delete": {"summary": "Delete instance"}
        },
        "/api/v1/instances/{instance_id}/pause": {
            "post": {"summary": "Pause instance"}
        },
        "/api/v1/instances/{instance_id}/resume": {
            "post": {"summary": "Resume instance"}
        },
        "/api/v1/snapshots": {
            "get": {"summary": "List snapshots"},
            "post": {"summary": "Create snapshot", "requestBody": {}}
        },
        "/api/v1/snapshots/{snapshot_id}": {
            "delete": {"summary": "Delete snapshot"}
        },
        "/api/v1/warmpool/status/{machine_id}": {
            "get": {"summary": "Get warm pool status"}
        },
        "/api/v1/warmpool/hosts": {
            "get": {"summary": "List multi-GPU hosts"}
        },
        "/api/v1/warmpool/provision": {
            "post": {"summary": "Provision warm pool", "requestBody": {}}
        },
        "/api/v1/failover/execute": {
            "post": {"summary": "Execute failover", "requestBody": {}}
        },
        "/api/v1/failover/status/{machine_id}": {
            "get": {"summary": "Get failover status"}
        },
        "/api/v1/failover/settings/global": {
            "get": {"summary": "Get global failover settings"},
            "put": {"summary": "Update global failover settings", "requestBody": {}}
        },
        "/api/v1/standby/status": {
            "get": {"summary": "Get standby status"}
        },
        "/api/v1/standby/configure": {
            "post": {"summary": "Configure standby", "requestBody": {}}
        },
        "/api/v1/balance": {
            "get": {"summary": "Get account balance"}
        },
        "/api/v1/settings": {
            "get": {"summary": "Get settings"},
            "put": {"summary": "Update settings", "requestBody": {}}
        },
    }
}


class TestAPIClient:
    """Tests for APIClient"""

    @pytest.fixture
    def api(self):
        """Create API client instance"""
        return APIClient(base_url="http://localhost:8766")

    def test_init(self, api):
        """Test API client initialization"""
        assert api.base_url == "http://localhost:8766"
        assert api.session is not None
        assert api.token_manager is not None

    def test_get_headers_no_token(self, api):
        """Test headers without token"""
        with patch.object(api.token_manager, 'get', return_value=None):
            headers = api._get_headers()
            assert headers["Content-Type"] == "application/json"
            assert "Authorization" not in headers

    def test_get_headers_with_token(self, api):
        """Test headers with token"""
        with patch.object(api.token_manager, 'get', return_value="test_token"):
            headers = api._get_headers()
            assert headers["Content-Type"] == "application/json"
            assert headers["Authorization"] == "Bearer test_token"

    @patch('requests.Session.get')
    def test_call_get_success(self, mock_get, api):
        """Test GET request success"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"instances": []}
        mock_get.return_value = mock_response

        result = api.call("GET", "/api/v1/instances", silent=True)
        assert result == {"instances": []}
        mock_get.assert_called_once()

    @patch('requests.Session.post')
    def test_call_post_success(self, mock_post, api):
        """Test POST request success"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "12345"}
        mock_post.return_value = mock_response

        result = api.call("POST", "/api/v1/instances", data={"gpu_name": "RTX 4090"}, silent=True)
        assert result == {"id": "12345"}
        mock_post.assert_called_once()

    @patch('requests.Session.post')
    def test_call_login_saves_token(self, mock_post, api):
        """Test login saves token"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_token",
            "token_type": "bearer"
        }
        mock_post.return_value = mock_response

        with patch.object(api.token_manager, 'save') as mock_save:
            result = api.call("POST", "/api/auth/login", data={"username": "test", "password": "pass"}, silent=True)
            assert result["access_token"] == "new_token"
            mock_save.assert_called_once_with("new_token")

    @patch('requests.Session.post')
    def test_call_logout_clears_token(self, mock_post, api):
        """Test logout clears token"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_post.return_value = mock_response

        with patch.object(api.token_manager, 'clear') as mock_clear:
            result = api.call("POST", "/api/auth/logout", silent=True)
            mock_clear.assert_called_once()

    @patch('requests.Session.get')
    def test_call_401_unauthorized(self, mock_get, api):
        """Test 401 unauthorized response"""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        result = api.call("GET", "/api/v1/instances", silent=True)
        assert result is None

    @patch('requests.Session.get')
    def test_call_404_not_found(self, mock_get, api):
        """Test 404 not found response"""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = api.call("GET", "/api/v1/instances/999", silent=True)
        assert result is None

    @patch('requests.Session.get')
    def test_call_connection_error(self, mock_get, api):
        """Test connection error"""
        mock_get.side_effect = Exception("Connection refused")

        result = api.call("GET", "/api/v1/instances", silent=True)
        assert result is None

    def test_call_unsupported_method(self, api):
        """Test unsupported HTTP method"""
        result = api.call("PATCH", "/api/v1/instances", silent=True)
        assert result is None


class TestCommandBuilder:
    """Tests for CommandBuilder with auto-discovery"""

    @pytest.fixture
    def api(self):
        """Create mock API client"""
        api = MagicMock()
        api.call = MagicMock()
        api.base_url = "http://localhost:8766"
        return api

    @pytest.fixture
    def builder(self, api):
        """Create CommandBuilder instance"""
        return CommandBuilder(api)

    def test_init(self, builder, api):
        """Test CommandBuilder initialization"""
        assert builder.api == api
        assert builder.commands_cache is None

    def test_build_command_tree_with_schema(self, builder, api):
        """Test building command tree from OpenAPI schema"""
        api.load_openapi_schema.return_value = MOCK_OPENAPI_SCHEMA

        commands = builder.build_command_tree()

        # Check auth commands
        assert "auth" in commands
        assert "login" in commands["auth"]
        assert "logout" in commands["auth"]
        assert "me" in commands["auth"]

        # Check instance commands
        assert "instance" in commands
        assert "list" in commands["instance"]
        assert "create" in commands["instance"]
        assert "get" in commands["instance"]
        assert "delete" in commands["instance"]
        assert "pause" in commands["instance"]
        assert "resume" in commands["instance"]

        # Check warmpool commands
        assert "warmpool" in commands
        assert "hosts" in commands["warmpool"]
        assert "provision" in commands["warmpool"]

    def test_build_command_tree_no_schema_exits(self, builder, api):
        """Test that missing schema causes exit"""
        api.load_openapi_schema.return_value = None

        with pytest.raises(SystemExit) as exc_info:
            builder.build_command_tree()

        assert exc_info.value.code == 1

    def test_execute_help_command(self, builder, api, capsys):
        """Test help command"""
        api.load_openapi_schema.return_value = MOCK_OPENAPI_SCHEMA

        builder.execute("help", None, [])

        captured = capsys.readouterr()
        assert "Dumont Cloud CLI" in captured.out
        assert "comandos disponíveis" in captured.out

    def test_execute_unknown_resource(self, builder, api):
        """Test unknown resource"""
        api.load_openapi_schema.return_value = MOCK_OPENAPI_SCHEMA

        with pytest.raises(SystemExit):
            builder.execute("unknown", "action", [])

    def test_execute_unknown_action(self, builder, api):
        """Test unknown action"""
        api.load_openapi_schema.return_value = MOCK_OPENAPI_SCHEMA

        with pytest.raises(SystemExit):
            builder.execute("instance", "unknown", [])

    def test_execute_simple_get(self, builder, api):
        """Test executing simple GET command"""
        api.load_openapi_schema.return_value = MOCK_OPENAPI_SCHEMA

        builder.execute("instance", "list", [])

        api.call.assert_called_once_with("GET", "/api/v1/instances", None, None)

    def test_execute_with_path_param(self, builder, api):
        """Test executing command with path parameter"""
        api.load_openapi_schema.return_value = MOCK_OPENAPI_SCHEMA

        builder.execute("instance", "get", ["12345"])

        api.call.assert_called_once_with("GET", "/api/v1/instances/12345", None, None)

    def test_execute_with_missing_path_param(self, builder, api):
        """Test executing command with missing path parameter"""
        api.load_openapi_schema.return_value = MOCK_OPENAPI_SCHEMA

        with pytest.raises(SystemExit):
            builder.execute("instance", "delete", [])

    def test_execute_login_with_credentials(self, builder, api):
        """Test login command with username and password"""
        api.load_openapi_schema.return_value = MOCK_OPENAPI_SCHEMA

        builder.execute("auth", "login", ["user@test.com", "password123"])

        api.call.assert_called_once()
        args = api.call.call_args
        assert args[0][0] == "POST"
        assert args[0][1] == "/api/auth/login"
        assert args[0][2] == {"username": "user@test.com", "password": "password123"}


class TestTokenManager:
    """Tests for TokenManager"""

    @pytest.fixture
    def token_manager(self, tmp_path):
        """Create TokenManager with temp file"""
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = tmp_path
            tm = TokenManager()
            yield tm

    def test_init(self, token_manager):
        """Test TokenManager initialization"""
        assert token_manager.token is None

    def test_save_and_get_token(self, token_manager):
        """Test saving and getting token"""
        token_manager.save("test_token_123")
        assert token_manager.get() == "test_token_123"

    def test_clear_token(self, token_manager):
        """Test clearing token"""
        token_manager.save("test_token")
        assert token_manager.get() == "test_token"

        token_manager.clear()
        assert token_manager.get() is None

    def test_get_nonexistent_token(self, token_manager):
        """Test getting token when file doesn't exist"""
        assert token_manager.get() is None


# ============================================================
# Auto-Discovery Command Tests
# ============================================================

class TestAutoDiscoveryCommands:
    """Tests for auto-discovered commands"""

    @pytest.fixture
    def builder(self):
        """Create CommandBuilder with mock API"""
        api = MagicMock()
        api.load_openapi_schema.return_value = MOCK_OPENAPI_SCHEMA
        api.base_url = "http://localhost:8766"
        return CommandBuilder(api)

    def test_auth_commands_discovered(self, builder):
        """Test auth commands are auto-discovered"""
        commands = builder.build_command_tree()
        assert "auth" in commands
        assert "login" in commands["auth"]
        assert "logout" in commands["auth"]
        assert "me" in commands["auth"]
        assert "register" in commands["auth"]

    def test_instance_commands_discovered(self, builder):
        """Test instance commands are auto-discovered"""
        commands = builder.build_command_tree()
        assert "instance" in commands
        assert "list" in commands["instance"]
        assert "create" in commands["instance"]
        assert "get" in commands["instance"]
        assert "delete" in commands["instance"]
        assert "pause" in commands["instance"]
        assert "resume" in commands["instance"]

    def test_snapshot_commands_discovered(self, builder):
        """Test snapshot commands are auto-discovered"""
        commands = builder.build_command_tree()
        assert "snapshot" in commands
        assert "list" in commands["snapshot"]
        assert "create" in commands["snapshot"]
        assert "delete" in commands["snapshot"]

    def test_warmpool_commands_discovered(self, builder):
        """Test warmpool commands are auto-discovered"""
        commands = builder.build_command_tree()
        assert "warmpool" in commands
        assert "hosts" in commands["warmpool"]
        assert "provision" in commands["warmpool"]
        # status has path param so check it exists
        assert any("status" in cmd for cmd in commands["warmpool"])

    def test_failover_commands_discovered(self, builder):
        """Test failover commands are auto-discovered"""
        commands = builder.build_command_tree()
        assert "failover" in commands
        assert "execute" in commands["failover"]

    def test_standby_commands_discovered(self, builder):
        """Test standby commands are auto-discovered"""
        commands = builder.build_command_tree()
        assert "standby" in commands
        assert "status" in commands["standby"]
        assert "configure" in commands["standby"]

    def test_balance_commands_discovered(self, builder):
        """Test balance commands are auto-discovered"""
        commands = builder.build_command_tree()
        assert "balance" in commands
        assert "list" in commands["balance"]

    def test_settings_commands_discovered(self, builder):
        """Test settings commands are auto-discovered"""
        commands = builder.build_command_tree()
        assert "settings" in commands


class TestCommandMethodMapping:
    """Tests for HTTP method mapping"""

    @pytest.fixture
    def builder(self):
        """Create CommandBuilder with mock API"""
        api = MagicMock()
        api.load_openapi_schema.return_value = MOCK_OPENAPI_SCHEMA
        api.base_url = "http://localhost:8766"
        return CommandBuilder(api)

    def test_get_method_mapped(self, builder):
        """Test GET methods are correctly mapped"""
        commands = builder.build_command_tree()
        assert commands["instance"]["list"]["method"] == "GET"
        assert commands["instance"]["get"]["method"] == "GET"

    def test_post_method_mapped(self, builder):
        """Test POST methods are correctly mapped"""
        commands = builder.build_command_tree()
        assert commands["instance"]["create"]["method"] == "POST"
        assert commands["auth"]["login"]["method"] == "POST"

    def test_delete_method_mapped(self, builder):
        """Test DELETE methods are correctly mapped"""
        commands = builder.build_command_tree()
        assert commands["instance"]["delete"]["method"] == "DELETE"

    def test_put_method_mapped(self, builder):
        """Test PUT methods are correctly mapped"""
        commands = builder.build_command_tree()
        assert commands["settings"]["update"]["method"] == "PUT"


class TestPathParsing:
    """Tests for path parameter handling"""

    @pytest.fixture
    def builder(self):
        """Create CommandBuilder with mock API"""
        api = MagicMock()
        api.load_openapi_schema.return_value = MOCK_OPENAPI_SCHEMA
        api.base_url = "http://localhost:8766"
        return CommandBuilder(api)

    def test_path_with_single_param(self, builder):
        """Test paths with single path parameter"""
        commands = builder.build_command_tree()
        assert "{instance_id}" in commands["instance"]["get"]["path"]

    def test_action_after_path_param(self, builder):
        """Test action name extraction after path param"""
        commands = builder.build_command_tree()
        # /instances/{id}/pause -> action should be "pause"
        assert "pause" in commands["instance"]
        assert "resume" in commands["instance"]


class TestIntegrationScenarios:
    """Integration-style tests for common workflows"""

    @pytest.fixture
    def api(self):
        """Create API client with mock session"""
        return APIClient(base_url="http://localhost:8766")

    @patch('requests.Session.post')
    @patch('requests.Session.get')
    def test_full_auth_workflow(self, mock_get, mock_post, api):
        """Test full authentication workflow: login -> me -> logout"""
        # Login
        login_response = Mock()
        login_response.ok = True
        login_response.status_code = 200
        login_response.json.return_value = {"access_token": "token123"}
        mock_post.return_value = login_response

        with patch.object(api.token_manager, 'save') as mock_save:
            result = api.call("POST", "/api/auth/login",
                            data={"username": "test", "password": "pass"},
                            silent=True)
            assert result["access_token"] == "token123"
            mock_save.assert_called_once_with("token123")

        # Get current user
        me_response = Mock()
        me_response.ok = True
        me_response.status_code = 200
        me_response.json.return_value = {"email": "test@test.com", "id": 1}
        mock_get.return_value = me_response

        with patch.object(api.token_manager, 'get', return_value="token123"):
            result = api.call("GET", "/api/auth/me", silent=True)
            assert result["email"] == "test@test.com"

        # Logout
        logout_response = Mock()
        logout_response.ok = True
        logout_response.status_code = 200
        logout_response.json.return_value = {"status": "success"}
        mock_post.return_value = logout_response

        with patch.object(api.token_manager, 'clear') as mock_clear:
            result = api.call("POST", "/api/auth/logout", silent=True)
            mock_clear.assert_called_once()

    @patch('requests.Session.get')
    def test_instance_list_workflow(self, mock_get, api):
        """Test listing instances"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "instances": [
                {"id": "1", "gpu_name": "RTX 4090", "status": "running"},
                {"id": "2", "gpu_name": "RTX 3090", "status": "paused"}
            ]
        }
        mock_get.return_value = mock_response

        result = api.call("GET", "/api/v1/instances", silent=True)

        assert len(result["instances"]) == 2
        assert result["instances"][0]["gpu_name"] == "RTX 4090"

    @patch('requests.Session.post')
    def test_snapshot_create_workflow(self, mock_post, api):
        """Test creating snapshot"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "snapshot_id": "snap_123",
            "name": "backup1",
            "instance_id": "12345"
        }
        mock_post.return_value = mock_response

        result = api.call("POST", "/api/v1/snapshots",
                         data={"name": "backup1", "instance_id": "12345"},
                         silent=True)

        assert result["snapshot_id"] == "snap_123"
        assert result["name"] == "backup1"


class TestBackendOffline:
    """Tests for backend offline scenarios"""

    def test_no_schema_exits_with_error(self):
        """Test that missing schema causes exit with code 1"""
        api = MagicMock()
        api.load_openapi_schema.return_value = None
        api.base_url = "http://localhost:8766"
        builder = CommandBuilder(api)

        with pytest.raises(SystemExit) as exc_info:
            builder.build_command_tree()

        assert exc_info.value.code == 1

    def test_error_message_shows_url(self, capsys):
        """Test that error message includes backend URL"""
        api = MagicMock()
        api.load_openapi_schema.return_value = None
        api.base_url = "http://localhost:8766"
        builder = CommandBuilder(api)

        with pytest.raises(SystemExit):
            builder.build_command_tree()

        captured = capsys.readouterr()
        assert "localhost:8766" in captured.out
        assert "backend" in captured.out.lower()
