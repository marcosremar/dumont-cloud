"""
Abstract interface for SSO configuration storage (Dependency Inversion Principle)
Allows swapping between database, file-based, or external providers
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime


class ISSORepository(ABC):
    """Abstract interface for SSO configuration and user mapping storage"""

    # ==================== SSO Config Operations ====================

    @abstractmethod
    def get_sso_config(self, organization_id: str) -> Optional[Dict[str, Any]]:
        """
        Get SSO configuration for an organization.

        Args:
            organization_id: The organization identifier

        Returns:
            SSO configuration dictionary or None if not found
        """
        pass

    @abstractmethod
    def get_sso_config_by_id(self, config_id: int) -> Optional[Dict[str, Any]]:
        """
        Get SSO configuration by its ID.

        Args:
            config_id: The SSO config ID

        Returns:
            SSO configuration dictionary or None if not found
        """
        pass

    @abstractmethod
    def create_sso_config(
        self,
        organization_id: str,
        provider_type: str,
        provider_name: str,
        config_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a new SSO configuration for an organization.

        Args:
            organization_id: The organization identifier
            provider_type: 'oidc' or 'saml'
            provider_name: 'okta', 'azure', 'google', etc.
            config_data: Provider-specific configuration data

        Returns:
            The created SSO configuration dictionary

        Raises:
            ValidationException: If config already exists or invalid data
        """
        pass

    @abstractmethod
    def update_sso_config(
        self,
        organization_id: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update SSO configuration for an organization.

        Args:
            organization_id: The organization identifier
            updates: Dictionary of fields to update

        Returns:
            The updated SSO configuration dictionary

        Raises:
            NotFoundException: If config not found
        """
        pass

    @abstractmethod
    def delete_sso_config(self, organization_id: str) -> bool:
        """
        Delete SSO configuration for an organization.

        Args:
            organization_id: The organization identifier

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    def enable_sso(self, organization_id: str) -> Dict[str, Any]:
        """
        Enable SSO for an organization.

        Args:
            organization_id: The organization identifier

        Returns:
            The updated SSO configuration dictionary

        Raises:
            NotFoundException: If config not found
            ValidationException: If config is incomplete
        """
        pass

    @abstractmethod
    def disable_sso(self, organization_id: str) -> Dict[str, Any]:
        """
        Disable SSO for an organization.

        Args:
            organization_id: The organization identifier

        Returns:
            The updated SSO configuration dictionary

        Raises:
            NotFoundException: If config not found
        """
        pass

    @abstractmethod
    def set_sso_enforcement(
        self,
        organization_id: str,
        enforced: bool,
        allow_fallback: bool = True,
    ) -> Dict[str, Any]:
        """
        Set SSO enforcement policy for an organization.

        Args:
            organization_id: The organization identifier
            enforced: Whether to enforce SSO (block password login)
            allow_fallback: Whether to allow password login if SSO fails

        Returns:
            The updated SSO configuration dictionary

        Raises:
            NotFoundException: If config not found
        """
        pass

    @abstractmethod
    def list_sso_configs(
        self,
        enabled_only: bool = False,
        provider_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all SSO configurations.

        Args:
            enabled_only: Only return enabled configurations
            provider_type: Filter by provider type ('oidc' or 'saml')

        Returns:
            List of SSO configuration dictionaries
        """
        pass

    @abstractmethod
    def get_sso_config_by_domain(self, email_domain: str) -> Optional[Dict[str, Any]]:
        """
        Get SSO configuration by email domain.

        Args:
            email_domain: The email domain (e.g., 'company.com')

        Returns:
            SSO configuration dictionary or None if not found
        """
        pass

    # ==================== SSO User Mapping Operations ====================

    @abstractmethod
    def get_sso_user_mapping(
        self,
        user_id: str,
        organization_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get SSO user mapping for a user in an organization.

        Args:
            user_id: The local user identifier
            organization_id: The organization identifier

        Returns:
            SSO user mapping dictionary or None if not found
        """
        pass

    @abstractmethod
    def get_sso_user_mapping_by_external_id(
        self,
        provider: str,
        external_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get SSO user mapping by external SSO identity.

        Args:
            provider: SSO provider name ('okta', 'azure', 'google')
            external_id: External user ID from the IdP

        Returns:
            SSO user mapping dictionary or None if not found
        """
        pass

    @abstractmethod
    def create_sso_user_mapping(
        self,
        user_id: str,
        organization_id: str,
        provider: str,
        external_id: str,
        mapping_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a new SSO user mapping.

        Args:
            user_id: The local user identifier
            organization_id: The organization identifier
            provider: SSO provider name
            external_id: External user ID from the IdP
            mapping_data: Additional mapping data (email, name, groups)

        Returns:
            The created SSO user mapping dictionary

        Raises:
            ValidationException: If mapping already exists
        """
        pass

    @abstractmethod
    def update_sso_user_mapping(
        self,
        user_id: str,
        organization_id: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update SSO user mapping.

        Args:
            user_id: The local user identifier
            organization_id: The organization identifier
            updates: Dictionary of fields to update

        Returns:
            The updated SSO user mapping dictionary

        Raises:
            NotFoundException: If mapping not found
        """
        pass

    @abstractmethod
    def delete_sso_user_mapping(
        self,
        user_id: str,
        organization_id: str,
    ) -> bool:
        """
        Delete SSO user mapping.

        Args:
            user_id: The local user identifier
            organization_id: The organization identifier

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    def list_sso_user_mappings(
        self,
        organization_id: str,
        active_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        List all SSO user mappings for an organization.

        Args:
            organization_id: The organization identifier
            active_only: Only return active (non-deprovisioned) mappings

        Returns:
            List of SSO user mapping dictionaries
        """
        pass

    # ==================== Audit & Statistics ====================

    @abstractmethod
    def record_sso_login(
        self,
        organization_id: str,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> None:
        """
        Record a successful SSO login for audit purposes.

        Args:
            organization_id: The organization identifier
            user_id: The local user identifier
            session_id: Optional SSO session ID
        """
        pass

    @abstractmethod
    def record_sso_error(
        self,
        organization_id: str,
        error_message: str,
    ) -> None:
        """
        Record an SSO error for debugging purposes.

        Args:
            organization_id: The organization identifier
            error_message: The error message
        """
        pass

    @abstractmethod
    def sync_user_from_idp(
        self,
        user_id: str,
        organization_id: str,
        idp_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Sync user data from IdP (groups, status, etc.).

        Args:
            user_id: The local user identifier
            organization_id: The organization identifier
            idp_data: Data from the IdP (groups, active status, etc.)

        Returns:
            The updated SSO user mapping dictionary

        Raises:
            NotFoundException: If mapping not found
        """
        pass

    @abstractmethod
    def deprovision_user(
        self,
        user_id: str,
        organization_id: str,
    ) -> Dict[str, Any]:
        """
        Mark a user as deprovisioned (removed from IdP).

        Args:
            user_id: The local user identifier
            organization_id: The organization identifier

        Returns:
            The updated SSO user mapping dictionary

        Raises:
            NotFoundException: If mapping not found
        """
        pass

    # ==================== Role Mapping ====================

    @abstractmethod
    def update_role_mappings(
        self,
        organization_id: str,
        role_mappings: Dict[str, str],
        default_role: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update IdP group to app role mappings.

        Args:
            organization_id: The organization identifier
            role_mappings: Dictionary mapping IdP groups to app roles
            default_role: Default role if no group matches

        Returns:
            The updated SSO configuration dictionary

        Raises:
            NotFoundException: If config not found
        """
        pass

    @abstractmethod
    def get_role_mappings(
        self,
        organization_id: str,
    ) -> Dict[str, Any]:
        """
        Get IdP group to app role mappings.

        Args:
            organization_id: The organization identifier

        Returns:
            Dictionary with 'mappings', 'default_role', and 'group_attribute'

        Raises:
            NotFoundException: If config not found
        """
        pass
