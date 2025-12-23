"""
Tests for the SettingsClient module.

Includes unit tests (with mocks) and integration tests (with real API).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from dumont_sdk.settings import (
    SettingsClient,
    UserSettings,
    AccountBalance,
)


# =============================================================================
# Mock Data
# =============================================================================

@pytest.fixture
def mock_settings_response():
    """Mock settings response."""
    return {
        "vast_api_key": "vast_sk_abc123...",
        "settings": {
            "has_completed_onboarding": True,
            "auto_hibernation_enabled": True,
            "hibernation_idle_minutes": 3,
            "default_gpu": "RTX_4090",
        },
    }


@pytest.fixture
def mock_balance_response():
    """Mock balance response."""
    return {
        "credit": 50.25,
        "balance": 45.50,
        "balance_threshold": 10.0,
        "email": "user@example.com",
    }


@pytest.fixture
def mock_cloud_storage_response():
    """Mock cloud storage settings response."""
    return {
        "settings": {
            "primary_provider": "backblaze_b2",
            "b2_key_id": "key_id_123",
            "b2_bucket_name": "my-backup-bucket",
            "enabled": True,
        }
    }


@pytest.fixture
def mock_success_response():
    """Mock success response."""
    return {
        "success": True,
        "message": "Operation completed successfully",
    }


@pytest.fixture
def mock_base_client():
    """Mock base client for unit tests."""
    client = MagicMock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.put = AsyncMock()
    return client


# =============================================================================
# Unit Tests
# =============================================================================

class TestSettingsUnit:
    """Unit tests for SettingsClient (using mocks)."""

    @pytest.mark.asyncio
    async def test_get_settings(self, mock_base_client, mock_settings_response):
        """Test getting user settings."""
        mock_base_client.get.return_value = mock_settings_response

        client = SettingsClient(mock_base_client)
        settings = await client.get()

        mock_base_client.get.assert_called_once_with("/api/v1/settings")

        assert isinstance(settings, UserSettings)
        assert settings.vast_api_key == "vast_sk_abc123..."
        assert settings.settings["has_completed_onboarding"] is True
        assert settings.settings["auto_hibernation_enabled"] is True

    @pytest.mark.asyncio
    async def test_update_settings(self, mock_base_client, mock_success_response):
        """Test updating user settings."""
        mock_base_client.put.return_value = mock_success_response

        client = SettingsClient(mock_base_client)
        result = await client.update(
            vast_api_key="new_vast_key",
            settings={"auto_hibernation_enabled": False},
        )

        mock_base_client.put.assert_called_once()
        call_args = mock_base_client.put.call_args
        assert call_args[0][0] == "/api/v1/settings"
        assert call_args[1]["data"]["vast_api_key"] == "new_vast_key"
        assert call_args[1]["data"]["settings"]["auto_hibernation_enabled"] is False

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_update_settings_partial(self, mock_base_client, mock_success_response):
        """Test partially updating settings."""
        mock_base_client.put.return_value = mock_success_response

        client = SettingsClient(mock_base_client)
        result = await client.update(
            settings={"default_gpu": "A100"},
        )

        mock_base_client.put.assert_called_once()
        call_args = mock_base_client.put.call_args
        assert "vast_api_key" not in call_args[1]["data"]
        assert call_args[1]["data"]["settings"]["default_gpu"] == "A100"

    @pytest.mark.asyncio
    async def test_get_balance(self, mock_base_client, mock_balance_response):
        """Test getting account balance."""
        mock_base_client.get.return_value = mock_balance_response

        client = SettingsClient(mock_base_client)
        balance = await client.balance()

        mock_base_client.get.assert_called_once_with("/api/balance")

        assert isinstance(balance, AccountBalance)
        assert balance.credit == 50.25
        assert balance.balance == 45.50
        assert balance.balance_threshold == 10.0
        assert balance.email == "user@example.com"

    @pytest.mark.asyncio
    async def test_complete_onboarding(self, mock_base_client, mock_success_response):
        """Test completing onboarding."""
        mock_base_client.post.return_value = mock_success_response

        client = SettingsClient(mock_base_client)
        result = await client.complete_onboarding()

        mock_base_client.post.assert_called_once_with("/api/v1/settings/complete-onboarding")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_get_cloud_storage(self, mock_base_client, mock_cloud_storage_response):
        """Test getting cloud storage settings."""
        mock_base_client.get.return_value = mock_cloud_storage_response

        client = SettingsClient(mock_base_client)
        settings = await client.get_cloud_storage()

        mock_base_client.get.assert_called_once_with("/api/v1/settings/cloud-storage")
        assert settings["primary_provider"] == "backblaze_b2"
        assert settings["b2_key_id"] == "key_id_123"

    @pytest.mark.asyncio
    async def test_update_cloud_storage(self, mock_base_client, mock_success_response):
        """Test updating cloud storage settings."""
        mock_base_client.put.return_value = mock_success_response

        client = SettingsClient(mock_base_client)
        result = await client.update_cloud_storage({
            "primary_provider": "aws_s3",
            "s3_access_key": "AKIAIOSFODNN7EXAMPLE",
            "s3_secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "s3_bucket_name": "my-backup-bucket",
            "s3_region": "us-east-1",
        })

        mock_base_client.put.assert_called_once()
        call_args = mock_base_client.put.call_args
        assert call_args[0][0] == "/api/v1/settings/cloud-storage"
        assert call_args[1]["data"]["primary_provider"] == "aws_s3"

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_test_cloud_storage(self, mock_base_client, mock_success_response):
        """Test testing cloud storage connection."""
        mock_base_client.post.return_value = mock_success_response

        client = SettingsClient(mock_base_client)
        result = await client.test_cloud_storage({
            "primary_provider": "backblaze_b2",
            "b2_key_id": "key_id_123",
            "b2_app_key": "app_key_456",
        })

        mock_base_client.post.assert_called_once()
        call_args = mock_base_client.post.call_args
        assert call_args[0][0] == "/api/v1/settings/cloud-storage/test"

        assert result["success"] is True


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.integration
class TestSettingsIntegration:
    """Integration tests for SettingsClient (requires real API)."""

    @pytest.mark.asyncio
    async def test_get_settings_real(self, client_with_api_key, rate_limiter):
        """Test getting settings from real API."""
        await rate_limiter.wait()

        settings = await client_with_api_key.settings.get()

        assert isinstance(settings, UserSettings)
        # Settings may have various fields depending on user config

    @pytest.mark.asyncio
    async def test_get_balance_real(self, client_with_api_key, rate_limiter):
        """Test getting balance from real API."""
        await rate_limiter.wait()

        balance = await client_with_api_key.settings.balance()

        assert isinstance(balance, AccountBalance)
        # Balance values depend on account state
        assert isinstance(balance.credit, (int, float))
        assert isinstance(balance.balance, (int, float))

    @pytest.mark.asyncio
    async def test_get_cloud_storage_real(self, client_with_api_key, rate_limiter):
        """Test getting cloud storage settings from real API."""
        await rate_limiter.wait()

        settings = await client_with_api_key.settings.get_cloud_storage()

        # Should return a dict (may be empty)
        assert isinstance(settings, dict)
