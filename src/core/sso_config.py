"""
SSO Configuration management for Dumont Cloud
Manages settings for Identity Providers (Okta, Azure AD, Google Workspace)
and SAML/OIDC protocol configuration
"""
from __future__ import annotations

from typing import Optional, List, Union, TYPE_CHECKING
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


class OktaSettings(BaseSettings):
    """Okta OIDC Configuration"""
    model_config = SettingsConfigDict(env_prefix="OKTA_", extra="ignore")

    domain: str = Field(default="", validation_alias=AliasChoices("domain", "OKTA_DOMAIN"))
    client_id: str = Field(default="", validation_alias=AliasChoices("client_id", "OKTA_CLIENT_ID"))
    client_secret: str = Field(default="", validation_alias=AliasChoices("client_secret", "OKTA_CLIENT_SECRET"))
    authorization_server_id: str = Field(
        default="default",
        validation_alias=AliasChoices("authorization_server_id", "OKTA_AUTHORIZATION_SERVER_ID")
    )

    @property
    def issuer(self) -> str:
        """Constructs the OIDC issuer URL"""
        if not self.domain:
            return ""
        return f"https://{self.domain}/oauth2/{self.authorization_server_id}"

    @property
    def authorization_endpoint(self) -> str:
        """Constructs the authorization endpoint URL"""
        return f"{self.issuer}/v1/authorize"

    @property
    def token_endpoint(self) -> str:
        """Constructs the token endpoint URL"""
        return f"{self.issuer}/v1/token"

    @property
    def userinfo_endpoint(self) -> str:
        """Constructs the userinfo endpoint URL"""
        return f"{self.issuer}/v1/userinfo"

    @property
    def jwks_uri(self) -> str:
        """Constructs the JWKS URI for token validation"""
        return f"{self.issuer}/v1/keys"

    @property
    def is_configured(self) -> bool:
        """Check if Okta is configured with required credentials"""
        return bool(self.domain and self.client_id and self.client_secret)


class AzureADSettings(BaseSettings):
    """Azure AD OIDC Configuration"""
    model_config = SettingsConfigDict(env_prefix="AZURE_", extra="ignore")

    tenant_id: str = Field(default="", validation_alias=AliasChoices("tenant_id", "AZURE_TENANT_ID"))
    client_id: str = Field(default="", validation_alias=AliasChoices("client_id", "AZURE_CLIENT_ID"))
    client_secret: str = Field(default="", validation_alias=AliasChoices("client_secret", "AZURE_CLIENT_SECRET"))

    @property
    def issuer(self) -> str:
        """Constructs the OIDC issuer URL for Azure AD"""
        if not self.tenant_id:
            return ""
        return f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"

    @property
    def authorization_endpoint(self) -> str:
        """Constructs the authorization endpoint URL"""
        if not self.tenant_id:
            return ""
        return f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/authorize"

    @property
    def token_endpoint(self) -> str:
        """Constructs the token endpoint URL"""
        if not self.tenant_id:
            return ""
        return f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"

    @property
    def userinfo_endpoint(self) -> str:
        """Constructs the userinfo endpoint URL"""
        return "https://graph.microsoft.com/oidc/userinfo"

    @property
    def jwks_uri(self) -> str:
        """Constructs the JWKS URI for token validation"""
        if not self.tenant_id:
            return ""
        return f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"

    @property
    def discovery_url(self) -> str:
        """Constructs the OpenID Connect discovery URL"""
        if not self.tenant_id:
            return ""
        return f"https://login.microsoftonline.com/{self.tenant_id}/v2.0/.well-known/openid-configuration"

    @property
    def is_configured(self) -> bool:
        """Check if Azure AD is configured with required credentials"""
        return bool(self.tenant_id and self.client_id and self.client_secret)


class GoogleSettings(BaseSettings):
    """Google Workspace OIDC Configuration"""
    model_config = SettingsConfigDict(env_prefix="GOOGLE_", extra="ignore")

    client_id: str = Field(default="", validation_alias=AliasChoices("client_id", "GOOGLE_CLIENT_ID"))
    client_secret: str = Field(default="", validation_alias=AliasChoices("client_secret", "GOOGLE_CLIENT_SECRET"))
    hosted_domain: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("hosted_domain", "GOOGLE_HOSTED_DOMAIN")
    )

    @property
    def issuer(self) -> str:
        """Google's OIDC issuer URL"""
        return "https://accounts.google.com"

    @property
    def authorization_endpoint(self) -> str:
        """Google's authorization endpoint URL"""
        return "https://accounts.google.com/o/oauth2/v2/auth"

    @property
    def token_endpoint(self) -> str:
        """Google's token endpoint URL"""
        return "https://oauth2.googleapis.com/token"

    @property
    def userinfo_endpoint(self) -> str:
        """Google's userinfo endpoint URL"""
        return "https://openidconnect.googleapis.com/v1/userinfo"

    @property
    def jwks_uri(self) -> str:
        """Google's JWKS URI for token validation"""
        return "https://www.googleapis.com/oauth2/v3/certs"

    @property
    def discovery_url(self) -> str:
        """Google's OpenID Connect discovery URL"""
        return "https://accounts.google.com/.well-known/openid-configuration"

    @property
    def is_configured(self) -> bool:
        """Check if Google is configured with required credentials"""
        return bool(self.client_id and self.client_secret)


class SAMLSettings(BaseSettings):
    """SAML 2.0 Service Provider Configuration"""
    model_config = SettingsConfigDict(env_prefix="SAML_", extra="ignore")

    # Service Provider identification
    sp_entity_id: str = Field(
        default="",
        validation_alias=AliasChoices("sp_entity_id", "SAML_SP_ENTITY_ID")
    )

    # Certificate paths for signing and encryption
    cert_file: str = Field(
        default="./certs/saml.crt",
        validation_alias=AliasChoices("cert_file", "SAML_CERT_FILE")
    )
    key_file: str = Field(
        default="./certs/saml.key",
        validation_alias=AliasChoices("key_file", "SAML_KEY_FILE")
    )

    # SAML security settings
    want_assertions_signed: bool = Field(
        default=True,
        validation_alias=AliasChoices("want_assertions_signed", "SAML_WANT_ASSERTIONS_SIGNED")
    )
    want_assertions_encrypted: bool = Field(
        default=False,
        validation_alias=AliasChoices("want_assertions_encrypted", "SAML_WANT_ASSERTIONS_ENCRYPTED")
    )
    authn_requests_signed: bool = Field(
        default=True,
        validation_alias=AliasChoices("authn_requests_signed", "SAML_AUTHN_REQUESTS_SIGNED")
    )

    # Clock skew tolerance in seconds (for timestamp validation)
    clock_skew_tolerance: int = Field(
        default=60,
        validation_alias=AliasChoices("clock_skew_tolerance", "SAML_CLOCK_SKEW_TOLERANCE")
    )

    @property
    def is_configured(self) -> bool:
        """Check if SAML SP is configured"""
        return bool(self.sp_entity_id)


class SSOGeneralSettings(BaseSettings):
    """General SSO settings"""
    model_config = SettingsConfigDict(env_prefix="SSO_", extra="ignore")

    # OAuth callback URL (used for all OIDC providers)
    callback_url: str = Field(
        default="http://localhost:8000/auth/callback",
        validation_alias=AliasChoices("callback_url", "SSO_CALLBACK_URL")
    )

    # Session settings
    session_timeout_hours: int = Field(
        default=24,
        validation_alias=AliasChoices("session_timeout_hours", "SSO_SESSION_TIMEOUT_HOURS")
    )

    # Default role for new SSO users
    default_role: str = Field(
        default="user",
        validation_alias=AliasChoices("default_role", "SSO_DEFAULT_ROLE")
    )

    # OIDC scopes to request (space-separated)
    oidc_scopes: str = Field(
        default="openid profile email groups",
        validation_alias=AliasChoices("oidc_scopes", "SSO_OIDC_SCOPES")
    )

    # Enable debug logging for SSO flows
    debug: bool = Field(
        default=False,
        validation_alias=AliasChoices("debug", "SSO_DEBUG")
    )

    @property
    def oidc_scopes_list(self) -> List[str]:
        """Returns OIDC scopes as a list"""
        return self.oidc_scopes.split()


class SSOSettings(BaseSettings):
    """Main SSO settings container"""
    model_config = SettingsConfigDict(extra="ignore")

    # Provider-specific settings
    okta: OktaSettings = Field(default_factory=OktaSettings)
    azure: AzureADSettings = Field(default_factory=AzureADSettings)
    google: GoogleSettings = Field(default_factory=GoogleSettings)

    # Protocol settings
    saml: SAMLSettings = Field(default_factory=SAMLSettings)

    # General SSO settings
    general: SSOGeneralSettings = Field(default_factory=SSOGeneralSettings)

    @property
    def configured_providers(self) -> List[str]:
        """Returns list of configured OIDC providers"""
        providers = []
        if self.okta.is_configured:
            providers.append("okta")
        if self.azure.is_configured:
            providers.append("azure")
        if self.google.is_configured:
            providers.append("google")
        return providers

    @property
    def has_configured_providers(self) -> bool:
        """Check if any SSO provider is configured"""
        return len(self.configured_providers) > 0

    def get_provider_settings(self, provider: str) -> Optional[Union[OktaSettings, AzureADSettings, GoogleSettings]]:
        """
        Get settings for a specific provider

        Args:
            provider: Provider name ('okta', 'azure', 'google')

        Returns:
            Provider settings or None if not found
        """
        provider_map = {
            "okta": self.okta,
            "azure": self.azure,
            "google": self.google,
        }
        return provider_map.get(provider.lower())


# Singleton instance
_sso_settings: Optional[SSOSettings] = None


def get_sso_settings() -> SSOSettings:
    """Get or create SSO settings singleton"""
    global _sso_settings
    if _sso_settings is None:
        _sso_settings = SSOSettings()
    return _sso_settings


# Convenience export
sso_settings = get_sso_settings()
