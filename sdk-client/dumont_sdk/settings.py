"""
Settings module.

Provides access to:
- User settings (API keys, preferences)
- Account balance
- Cloud storage configuration for failover
- Onboarding status
"""
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class UserSettings:
    """User settings."""
    vast_api_key: Optional[str]
    settings: Optional[Dict[str, Any]]


@dataclass
class AccountBalance:
    """Account balance information."""
    credit: float
    balance: float
    balance_threshold: float
    email: str


@dataclass
class CloudStorageSettings:
    """Cloud storage failover settings."""
    primary_provider: Optional[str]
    b2_key_id: Optional[str]
    b2_app_key: Optional[str]
    b2_bucket_name: Optional[str]
    s3_access_key: Optional[str]
    s3_secret_key: Optional[str]
    s3_bucket_name: Optional[str]
    s3_region: Optional[str]
    gcs_credentials_json: Optional[str]
    gcs_bucket_name: Optional[str]


class SettingsClient:
    """
    Client for Settings operations.

    Manages user settings, account balance, and cloud storage configuration.

    Example:
        async with DumontClient(api_key="...") as client:
            # Get settings
            settings = await client.settings.get()

            # Get balance
            balance = await client.settings.balance()

            # Update cloud storage
            await client.settings.update_cloud_storage({
                "primary_provider": "backblaze_b2",
                "b2_key_id": "...",
                "b2_app_key": "...",
            })
    """

    def __init__(self, base_client):
        self._client = base_client

    async def get(self) -> UserSettings:
        """
        Get user settings.

        Returns current user settings including API keys and preferences.

        Returns:
            UserSettings with vast_api_key and settings dict
        """
        response = await self._client.get("/api/v1/settings")

        return UserSettings(
            vast_api_key=response.get("vast_api_key"),
            settings=response.get("settings"),
        )

    async def update(
        self,
        vast_api_key: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Update user settings.

        Args:
            vast_api_key: New Vast.ai API key
            settings: Settings dictionary to update

        Returns:
            Success response
        """
        data = {}
        if vast_api_key is not None:
            data["vast_api_key"] = vast_api_key
        if settings is not None:
            data["settings"] = settings

        return await self._client.put("/api/v1/settings", data=data)

    async def balance(self) -> AccountBalance:
        """
        Get account balance from Vast.ai.

        Returns:
            AccountBalance with credit, balance, and threshold
        """
        response = await self._client.get("/api/balance")

        return AccountBalance(
            credit=response.get("credit", 0),
            balance=response.get("balance", 0),
            balance_threshold=response.get("balance_threshold", 0),
            email=response.get("email", ""),
        )

    async def complete_onboarding(self) -> Dict[str, Any]:
        """
        Mark onboarding as completed.

        Returns:
            Success response
        """
        return await self._client.post("/api/v1/settings/complete-onboarding")

    # =========================================================================
    # Cloud Storage Settings
    # =========================================================================

    async def get_cloud_storage(self) -> Dict[str, Any]:
        """
        Get cloud storage failover settings.

        Returns:
            Cloud storage configuration
        """
        response = await self._client.get("/api/v1/settings/cloud-storage")
        return response.get("settings", {})

    async def update_cloud_storage(
        self,
        settings: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update cloud storage failover settings.

        Args:
            settings: Cloud storage configuration:
                - primary_provider: backblaze_b2, aws_s3, google_gcs, cloudflare_r2
                - b2_key_id, b2_app_key, b2_bucket_name (for B2)
                - s3_access_key, s3_secret_key, s3_bucket_name, s3_region (for S3)
                - gcs_credentials_json, gcs_bucket_name (for GCS)

        Returns:
            Success response
        """
        return await self._client.put("/api/v1/settings/cloud-storage", data=settings)

    async def test_cloud_storage(
        self,
        settings: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Test cloud storage connection.

        Args:
            settings: Cloud storage configuration to test

        Returns:
            Success response with validation result
        """
        return await self._client.post("/api/v1/settings/cloud-storage/test", data=settings)
