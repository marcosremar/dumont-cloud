"""
SAML Service - Domain Service (Business Logic)
Handles SAML 2.0 SP-initiated authentication with enterprise identity providers
"""
import logging
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timezone

from saml2 import BINDING_HTTP_POST, BINDING_HTTP_REDIRECT
from saml2.client import Saml2Client
from saml2.config import Config as Saml2Config
from saml2.response import AuthnResponse
from saml2.saml import NAMEID_FORMAT_EMAILADDRESS, NAMEID_FORMAT_UNSPECIFIED
from saml2.s_utils import factory
from saml2.sigver import SigverError, SignatureError
from saml2.validate import valid_instance

from ...core.exceptions import (
    AuthenticationException,
    ValidationException,
    ConfigurationException,
)
from ...core.sso_config import get_sso_settings, SAMLSettings

logger = logging.getLogger(__name__)


class SAMLProvider(str, Enum):
    """Supported SAML identity providers"""
    OKTA = "okta"
    AZURE = "azure"
    GOOGLE = "google"
    CUSTOM = "custom"


@dataclass
class SAMLIdPConfig:
    """Identity Provider configuration for SAML authentication"""
    provider_name: str
    entity_id: str
    sso_url: str
    slo_url: Optional[str] = None
    certificate: Optional[str] = None
    metadata_url: Optional[str] = None
    name_id_format: str = NAMEID_FORMAT_EMAILADDRESS


@dataclass
class SAMLUserInfo:
    """Extracted user information from SAML assertion"""
    name_id: str  # Subject identifier from SAML assertion
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    groups: Optional[List[str]] = None
    session_index: Optional[str] = None
    session_not_on_or_after: Optional[datetime] = None
    raw_attributes: Optional[Dict[str, Any]] = None


@dataclass
class SAMLAuthRequest:
    """SAML Authentication Request information"""
    request_id: str
    redirect_url: str
    relay_state: Optional[str] = None


class SAMLService:
    """
    Domain service for SAML 2.0 SP-initiated authentication.
    Handles Service Provider configuration, metadata generation, and assertion processing.
    """

    # Standard SAML attribute names
    ATTR_EMAIL = [
        "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
        "email",
        "Email",
        "mail",
        "http://schemas.microsoft.com/identity/claims/emailaddress",
    ]
    ATTR_FIRST_NAME = [
        "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
        "firstName",
        "first_name",
        "givenName",
        "FirstName",
    ]
    ATTR_LAST_NAME = [
        "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
        "lastName",
        "last_name",
        "surname",
        "LastName",
        "sn",
    ]
    ATTR_DISPLAY_NAME = [
        "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
        "displayName",
        "name",
        "cn",
        "fullName",
    ]
    ATTR_GROUPS = [
        "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups",
        "http://schemas.xmlsoap.org/claims/Group",
        "groups",
        "memberOf",
        "role",
        "roles",
    ]

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize SAML service with SP configuration.

        Args:
            base_url: Base URL for the application (used for SP endpoints)
        """
        self._sso_settings = get_sso_settings()
        self._saml_settings: SAMLSettings = self._sso_settings.saml
        self._base_url = base_url or self._sso_settings.general.callback_url.rsplit("/", 1)[0]
        self._sp_config: Optional[Dict[str, Any]] = None
        self._idp_configs: Dict[str, SAMLIdPConfig] = {}
        self._saml_clients: Dict[str, Saml2Client] = {}

        # Initialize SP configuration if settings are present
        if self._saml_settings.is_configured:
            self._initialize_sp_config()

    def _initialize_sp_config(self) -> None:
        """
        Initialize SAML Service Provider configuration.

        Raises:
            ConfigurationException: If required files are missing
        """
        entity_id = self._saml_settings.sp_entity_id

        # Build endpoint URLs
        acs_url = f"{self._base_url}/api/v1/saml/acs"
        slo_url = f"{self._base_url}/api/v1/saml/sls"
        metadata_url = f"{self._base_url}/api/v1/saml/metadata"

        # Read certificate and key files if they exist
        cert_content = None
        key_content = None

        if self._saml_settings.cert_file and os.path.exists(self._saml_settings.cert_file):
            try:
                with open(self._saml_settings.cert_file, "r") as f:
                    cert_content = f.read()
            except IOError as e:
                logger.warning(f"Could not read SAML certificate file: {e}")

        if self._saml_settings.key_file and os.path.exists(self._saml_settings.key_file):
            try:
                with open(self._saml_settings.key_file, "r") as f:
                    key_content = f.read()
            except IOError as e:
                logger.warning(f"Could not read SAML key file: {e}")

        # Build base SP configuration
        self._sp_config = {
            "entityid": entity_id,
            "service": {
                "sp": {
                    "name": "Dumont Cloud",
                    "name_id_format": [NAMEID_FORMAT_EMAILADDRESS, NAMEID_FORMAT_UNSPECIFIED],
                    "endpoints": {
                        "assertion_consumer_service": [
                            (acs_url, BINDING_HTTP_POST),
                        ],
                        "single_logout_service": [
                            (slo_url, BINDING_HTTP_POST),
                            (slo_url, BINDING_HTTP_REDIRECT),
                        ],
                    },
                    "allow_unsolicited": False,
                    "authn_requests_signed": self._saml_settings.authn_requests_signed,
                    "want_assertions_signed": self._saml_settings.want_assertions_signed,
                    "want_response_signed": True,
                    "want_assertions_encrypted": self._saml_settings.want_assertions_encrypted,
                },
            },
            "metadata": {
                "local": [],  # Will be populated with IdP metadata paths
            },
            "accepted_time_diff": self._saml_settings.clock_skew_tolerance,
            "debug": self._sso_settings.general.debug,
        }

        # Add certificate and key if available
        if cert_content and key_content:
            self._sp_config["cert_file"] = self._saml_settings.cert_file
            self._sp_config["key_file"] = self._saml_settings.key_file

        logger.info(f"SAML SP initialized with entity ID: {entity_id}")

    def is_configured(self) -> bool:
        """
        Check if SAML SP is configured.

        Returns:
            True if SAML settings are configured
        """
        return self._saml_settings.is_configured

    def get_sp_entity_id(self) -> str:
        """
        Get the Service Provider entity ID.

        Returns:
            SP entity ID string

        Raises:
            ConfigurationException: If SAML is not configured
        """
        if not self.is_configured():
            raise ConfigurationException(
                "SAML Service Provider is not configured",
                {"required": ["SAML_SP_ENTITY_ID"]},
            )
        return self._saml_settings.sp_entity_id

    def get_sp_metadata(self) -> str:
        """
        Generate SAML Service Provider metadata XML.

        Returns:
            SP metadata XML string

        Raises:
            ConfigurationException: If SAML is not configured
        """
        if not self.is_configured():
            raise ConfigurationException(
                "SAML Service Provider is not configured",
                {"required": ["SAML_SP_ENTITY_ID"]},
            )

        # Create a minimal config for metadata generation
        config = Saml2Config()
        config.load(self._sp_config)

        # Generate metadata
        metadata = factory(
            "md:EntityDescriptor",
            entityID=config.entityid,
        )

        # Build SP descriptor
        sp_sso_descriptor = config.generate_sp_metadata()

        return sp_sso_descriptor

    def register_idp(self, idp_config: SAMLIdPConfig) -> None:
        """
        Register an Identity Provider configuration.

        Args:
            idp_config: IdP configuration to register

        Raises:
            ValidationException: If IdP configuration is invalid
        """
        if not idp_config.entity_id:
            raise ValidationException(
                "IdP entity ID is required",
                {"field": "entity_id"},
            )

        if not idp_config.sso_url:
            raise ValidationException(
                "IdP SSO URL is required",
                {"field": "sso_url"},
            )

        self._idp_configs[idp_config.provider_name] = idp_config

        # Clear cached client for this provider
        self._saml_clients.pop(idp_config.provider_name, None)

        logger.info(f"Registered SAML IdP: {idp_config.provider_name} ({idp_config.entity_id})")

    def get_registered_idps(self) -> List[str]:
        """
        Get list of registered Identity Providers.

        Returns:
            List of registered IdP names
        """
        return list(self._idp_configs.keys())

    def _get_saml_client(self, provider_name: str) -> Saml2Client:
        """
        Get or create a SAML client for a provider.

        Args:
            provider_name: Name of the IdP

        Returns:
            Configured Saml2Client

        Raises:
            ConfigurationException: If provider is not registered
        """
        if provider_name in self._saml_clients:
            return self._saml_clients[provider_name]

        if provider_name not in self._idp_configs:
            raise ConfigurationException(
                f"SAML IdP '{provider_name}' is not registered",
                {"provider": provider_name, "registered": self.get_registered_idps()},
            )

        idp_config = self._idp_configs[provider_name]

        # Build configuration with IdP metadata inline
        config_dict = dict(self._sp_config)

        # Add IdP metadata inline
        config_dict["metadata"] = {
            "inline": [self._build_idp_metadata_xml(idp_config)],
        }

        config = Saml2Config()
        config.load(config_dict)

        client = Saml2Client(config)
        self._saml_clients[provider_name] = client

        return client

    def _build_idp_metadata_xml(self, idp_config: SAMLIdPConfig) -> str:
        """
        Build IdP metadata XML from configuration.

        Args:
            idp_config: IdP configuration

        Returns:
            IdP metadata XML string
        """
        cert_element = ""
        if idp_config.certificate:
            # Clean certificate - remove headers and whitespace
            cert_clean = idp_config.certificate.replace("-----BEGIN CERTIFICATE-----", "")
            cert_clean = cert_clean.replace("-----END CERTIFICATE-----", "")
            cert_clean = cert_clean.strip().replace("\n", "")
            cert_element = f"""
            <KeyDescriptor use="signing">
                <ds:KeyInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                    <ds:X509Data>
                        <ds:X509Certificate>{cert_clean}</ds:X509Certificate>
                    </ds:X509Data>
                </ds:KeyInfo>
            </KeyDescriptor>
            """

        slo_element = ""
        if idp_config.slo_url:
            slo_element = f"""
            <SingleLogoutService
                Binding="{BINDING_HTTP_REDIRECT}"
                Location="{idp_config.slo_url}"/>
            """

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<EntityDescriptor
    xmlns="urn:oasis:names:tc:SAML:2.0:metadata"
    entityID="{idp_config.entity_id}">
    <IDPSSODescriptor
        WantAuthnRequestsSigned="{str(self._saml_settings.authn_requests_signed).lower()}"
        protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        {cert_element}
        <NameIDFormat>{idp_config.name_id_format}</NameIDFormat>
        <SingleSignOnService
            Binding="{BINDING_HTTP_REDIRECT}"
            Location="{idp_config.sso_url}"/>
        <SingleSignOnService
            Binding="{BINDING_HTTP_POST}"
            Location="{idp_config.sso_url}"/>
        {slo_element}
    </IDPSSODescriptor>
</EntityDescriptor>
"""

    def create_authn_request(
        self,
        provider_name: str,
        relay_state: Optional[str] = None,
        force_authn: bool = False,
        name_id_format: Optional[str] = None,
    ) -> SAMLAuthRequest:
        """
        Create a SAML AuthnRequest for SP-initiated SSO.

        Args:
            provider_name: Name of the IdP to authenticate with
            relay_state: Optional state to preserve across the SSO flow
            force_authn: Force re-authentication even if user has session
            name_id_format: Override NameID format for this request

        Returns:
            SAMLAuthRequest with request details

        Raises:
            ConfigurationException: If SAML SP or IdP is not configured
        """
        if not self.is_configured():
            raise ConfigurationException(
                "SAML Service Provider is not configured",
                {"required": ["SAML_SP_ENTITY_ID"]},
            )

        client = self._get_saml_client(provider_name)
        idp_config = self._idp_configs[provider_name]

        # Build AuthnRequest
        nameid_format = name_id_format or idp_config.name_id_format

        try:
            request_id, info = client.prepare_for_authenticate(
                entityid=idp_config.entity_id,
                relay_state=relay_state,
                binding=BINDING_HTTP_REDIRECT,
                force_authn=force_authn,
                nameid_format=nameid_format,
            )
        except Exception as e:
            logger.error(f"Failed to create SAML AuthnRequest: {e}")
            raise ConfigurationException(
                f"Failed to create SAML authentication request: {str(e)}",
                {"provider": provider_name},
            )

        # Extract redirect URL from headers
        redirect_url = None
        for key, value in info["headers"]:
            if key.lower() == "location":
                redirect_url = value
                break

        if not redirect_url:
            raise ConfigurationException(
                "Failed to get redirect URL from SAML request",
                {"provider": provider_name},
            )

        logger.info(f"Created SAML AuthnRequest {request_id} for provider {provider_name}")

        return SAMLAuthRequest(
            request_id=request_id,
            redirect_url=redirect_url,
            relay_state=relay_state,
        )

    def process_saml_response(
        self,
        provider_name: str,
        saml_response: str,
        request_id: Optional[str] = None,
    ) -> SAMLUserInfo:
        """
        Process and validate a SAML Response/Assertion.

        Performs full validation:
        - Signature verification
        - Timestamp validation (with clock skew tolerance)
        - Audience restriction
        - Subject confirmation

        Args:
            provider_name: Name of the IdP
            saml_response: Base64-encoded SAML Response
            request_id: Original AuthnRequest ID for InResponseTo validation

        Returns:
            SAMLUserInfo with extracted user attributes

        Raises:
            AuthenticationException: If SAML response validation fails
        """
        if not self.is_configured():
            raise ConfigurationException(
                "SAML Service Provider is not configured",
            )

        client = self._get_saml_client(provider_name)

        try:
            # Parse and validate the SAML response
            authn_response = client.parse_authn_request_response(
                saml_response,
                BINDING_HTTP_POST,
                outstanding=({request_id: ""} if request_id else None),
            )

            if authn_response is None:
                raise AuthenticationException(
                    "Invalid SAML response - parsing failed",
                    {"provider": provider_name},
                )

            # Get the identity information
            identity = authn_response.get_identity()
            if not identity:
                raise AuthenticationException(
                    "No identity information in SAML response",
                    {"provider": provider_name},
                )

            # Get NameID (subject)
            name_id = authn_response.name_id
            if not name_id or not name_id.text:
                raise AuthenticationException(
                    "No NameID in SAML response",
                    {"provider": provider_name},
                )

            # Extract user info from attributes
            user_info = self._extract_user_info(
                name_id=name_id.text,
                attributes=identity,
                authn_response=authn_response,
            )

            logger.info(
                f"SAML authentication successful for {user_info.name_id} via {provider_name}"
            )

            return user_info

        except SigverError as e:
            logger.warning(f"SAML signature verification failed: {e}")
            raise AuthenticationException(
                "SAML signature verification failed",
                {"provider": provider_name, "error": str(e)},
            )
        except SignatureError as e:
            logger.warning(f"SAML signature error: {e}")
            raise AuthenticationException(
                "Invalid SAML signature",
                {"provider": provider_name, "error": str(e)},
            )
        except Exception as e:
            logger.error(f"SAML response processing failed: {e}")
            raise AuthenticationException(
                f"SAML response validation failed: {str(e)}",
                {"provider": provider_name},
            )

    def _extract_user_info(
        self,
        name_id: str,
        attributes: Dict[str, List[str]],
        authn_response: AuthnResponse,
    ) -> SAMLUserInfo:
        """
        Extract user information from SAML attributes.

        Args:
            name_id: Subject NameID value
            attributes: SAML attribute statement
            authn_response: Full AuthnResponse object

        Returns:
            SAMLUserInfo with extracted attributes
        """
        # Helper to find first matching attribute value
        def get_attr(attr_names: List[str]) -> Optional[str]:
            for attr_name in attr_names:
                if attr_name in attributes:
                    values = attributes[attr_name]
                    if values and len(values) > 0:
                        return values[0]
            return None

        # Helper to get list attribute
        def get_list_attr(attr_names: List[str]) -> Optional[List[str]]:
            for attr_name in attr_names:
                if attr_name in attributes:
                    return list(attributes[attr_name])
            return None

        # Extract session info
        session_index = None
        session_not_on_or_after = None

        try:
            session_info = authn_response.session_info()
            session_index = session_info.get("session_index")
            not_on_or_after = session_info.get("not_on_or_after")
            if not_on_or_after:
                if isinstance(not_on_or_after, str):
                    session_not_on_or_after = datetime.fromisoformat(
                        not_on_or_after.replace("Z", "+00:00")
                    )
                elif isinstance(not_on_or_after, datetime):
                    session_not_on_or_after = not_on_or_after
        except Exception as e:
            logger.debug(f"Could not extract session info: {e}")

        return SAMLUserInfo(
            name_id=name_id,
            email=get_attr(self.ATTR_EMAIL),
            first_name=get_attr(self.ATTR_FIRST_NAME),
            last_name=get_attr(self.ATTR_LAST_NAME),
            display_name=get_attr(self.ATTR_DISPLAY_NAME),
            groups=get_list_attr(self.ATTR_GROUPS),
            session_index=session_index,
            session_not_on_or_after=session_not_on_or_after,
            raw_attributes=dict(attributes),
        )

    def create_logout_request(
        self,
        provider_name: str,
        name_id: str,
        session_index: Optional[str] = None,
        relay_state: Optional[str] = None,
    ) -> Optional[str]:
        """
        Create a SAML LogoutRequest for Single Logout.

        Args:
            provider_name: Name of the IdP
            name_id: User's NameID value
            session_index: Session index from authentication
            relay_state: Optional state to preserve

        Returns:
            Redirect URL for logout, or None if SLO is not supported

        Raises:
            ConfigurationException: If IdP is not registered
        """
        if provider_name not in self._idp_configs:
            raise ConfigurationException(
                f"SAML IdP '{provider_name}' is not registered",
                {"provider": provider_name},
            )

        idp_config = self._idp_configs[provider_name]

        if not idp_config.slo_url:
            logger.warning(f"SLO not configured for provider {provider_name}")
            return None

        client = self._get_saml_client(provider_name)

        try:
            # Create logout request
            result = client.global_logout(
                name_id=name_id,
                session_indexes=[session_index] if session_index else None,
                binding=BINDING_HTTP_REDIRECT,
            )

            # Extract redirect URL
            for entity_id, logout_info in result.items():
                if "headers" in logout_info:
                    for key, value in logout_info["headers"]:
                        if key.lower() == "location":
                            logger.info(f"Created SAML logout request for {provider_name}")
                            return value

            return None

        except Exception as e:
            logger.error(f"Failed to create SAML logout request: {e}")
            return None

    def process_logout_response(
        self,
        provider_name: str,
        saml_response: str,
    ) -> bool:
        """
        Process a SAML LogoutResponse.

        Args:
            provider_name: Name of the IdP
            saml_response: Base64-encoded SAML LogoutResponse

        Returns:
            True if logout was successful, False otherwise
        """
        if provider_name not in self._idp_configs:
            logger.warning(f"Unknown provider in logout response: {provider_name}")
            return False

        try:
            client = self._get_saml_client(provider_name)
            response = client.parse_logout_request_response(
                saml_response,
                BINDING_HTTP_POST,
            )

            if response:
                logger.info(f"SAML logout successful for provider {provider_name}")
                return True

            return False

        except Exception as e:
            logger.warning(f"SAML logout response processing failed: {e}")
            return False

    def get_idp_metadata_url(self, provider: str) -> Optional[str]:
        """
        Get the standard metadata URL for well-known providers.

        Args:
            provider: Provider type ('okta', 'azure', 'google')

        Returns:
            Metadata URL template or None
        """
        metadata_urls = {
            SAMLProvider.OKTA.value: "https://{domain}/app/{app_id}/sso/saml/metadata",
            SAMLProvider.AZURE.value: "https://login.microsoftonline.com/{tenant_id}/federationmetadata/2007-06/federationmetadata.xml",
            SAMLProvider.GOOGLE.value: "https://accounts.google.com/o/saml2?idpid={idp_id}",
        }
        return metadata_urls.get(provider.lower())


# Singleton instance
_saml_service: Optional[SAMLService] = None


def get_saml_service(base_url: Optional[str] = None) -> SAMLService:
    """
    Get or create SAML service singleton.

    Args:
        base_url: Optional base URL (only used on first creation)

    Returns:
        SAMLService instance
    """
    global _saml_service
    if _saml_service is None:
        _saml_service = SAMLService(base_url)
    return _saml_service
