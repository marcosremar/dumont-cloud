"""
OIDC Service - Domain Service (Business Logic)
Handles OpenID Connect authentication with Okta, Azure AD, and Google providers
"""
import logging
import secrets
import hashlib
import base64
from typing import Optional, Dict, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlencode

from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.jose import jwt, JsonWebKey
from authlib.jose.errors import JoseError
import httpx

from ...core.exceptions import (
    AuthenticationException,
    ValidationException,
    ConfigurationException,
)
from ...core.sso_config import get_sso_settings, OktaSettings, AzureADSettings, GoogleSettings

logger = logging.getLogger(__name__)


class OIDCProvider(str, Enum):
    """Supported OIDC providers"""
    OKTA = "okta"
    AZURE = "azure"
    GOOGLE = "google"


@dataclass
class OIDCTokens:
    """Container for OIDC tokens"""
    access_token: str
    id_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: Optional[int] = None
    scope: Optional[str] = None


@dataclass
class OIDCUserInfo:
    """Extracted user information from OIDC tokens"""
    sub: str  # Subject (unique user ID from IdP)
    email: str
    email_verified: bool = False
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture: Optional[str] = None
    groups: Optional[list] = None
    raw_claims: Optional[Dict[str, Any]] = None


class OIDCService:
    """
    Domain service for OpenID Connect authentication.
    Handles OAuth 2.0 authorization code flow with PKCE for Okta, Azure AD, and Google.
    """

    # PKCE code verifier length (recommended: 43-128 characters)
    CODE_VERIFIER_LENGTH = 64

    def __init__(self):
        """Initialize OIDC service with SSO configuration"""
        self._sso_settings = get_sso_settings()
        self._jwks_cache: Dict[str, Dict[str, Any]] = {}

    def get_configured_providers(self) -> list:
        """
        Get list of configured OIDC providers.

        Returns:
            List of provider names that are properly configured
        """
        return self._sso_settings.configured_providers

    def is_provider_configured(self, provider: str) -> bool:
        """
        Check if a specific provider is configured.

        Args:
            provider: Provider name ('okta', 'azure', 'google')

        Returns:
            True if provider is configured with required credentials
        """
        provider_settings = self._sso_settings.get_provider_settings(provider)
        return provider_settings is not None and provider_settings.is_configured

    def _get_provider_settings(
        self, provider: str
    ) -> Union[OktaSettings, AzureADSettings, GoogleSettings]:
        """
        Get settings for a provider with validation.

        Args:
            provider: Provider name

        Returns:
            Provider settings object

        Raises:
            ConfigurationException: If provider is not configured
        """
        provider_settings = self._sso_settings.get_provider_settings(provider)
        if provider_settings is None:
            raise ConfigurationException(
                f"Unknown OIDC provider: {provider}",
                {"valid_providers": ["okta", "azure", "google"]},
            )

        if not provider_settings.is_configured:
            raise ConfigurationException(
                f"OIDC provider '{provider}' is not configured",
                {"provider": provider},
            )

        return provider_settings

    def generate_pkce_pair(self) -> Tuple[str, str]:
        """
        Generate PKCE code verifier and challenge.

        Returns:
            Tuple of (code_verifier, code_challenge)
        """
        # Generate cryptographically random code verifier
        code_verifier = secrets.token_urlsafe(self.CODE_VERIFIER_LENGTH)

        # Create code challenge using S256 method
        code_challenge_bytes = hashlib.sha256(code_verifier.encode("ascii")).digest()
        code_challenge = base64.urlsafe_b64encode(code_challenge_bytes).rstrip(b"=").decode("ascii")

        return code_verifier, code_challenge

    def generate_state(self) -> str:
        """
        Generate a cryptographically random state parameter for CSRF protection.

        Returns:
            Random state string
        """
        return secrets.token_urlsafe(32)

    def generate_nonce(self) -> str:
        """
        Generate a cryptographically random nonce for ID token validation.

        Returns:
            Random nonce string
        """
        return secrets.token_urlsafe(32)

    def build_authorization_url(
        self,
        provider: str,
        redirect_uri: str,
        state: str,
        nonce: str,
        code_challenge: str,
        scopes: Optional[list] = None,
        login_hint: Optional[str] = None,
    ) -> str:
        """
        Build the authorization URL for initiating OIDC login.

        Args:
            provider: OIDC provider name ('okta', 'azure', 'google')
            redirect_uri: OAuth callback URL
            state: CSRF protection state
            nonce: ID token replay protection nonce
            code_challenge: PKCE code challenge
            scopes: Optional list of scopes (defaults to configured scopes)
            login_hint: Optional email hint for pre-filling login form

        Returns:
            Full authorization URL

        Raises:
            ConfigurationException: If provider is not configured
        """
        provider_settings = self._get_provider_settings(provider)

        # Use default scopes if not provided
        if scopes is None:
            scopes = self._sso_settings.general.oidc_scopes_list

        # Build authorization parameters
        params = {
            "client_id": provider_settings.client_id,
            "response_type": "code",
            "scope": " ".join(scopes),
            "redirect_uri": redirect_uri,
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        # Add login hint if provided
        if login_hint:
            params["login_hint"] = login_hint

        # Provider-specific parameters
        if provider == OIDCProvider.GOOGLE.value:
            google_settings: GoogleSettings = provider_settings
            # Add hosted domain restriction for Google Workspace
            if google_settings.hosted_domain:
                params["hd"] = google_settings.hosted_domain
            # Request offline access for refresh tokens
            params["access_type"] = "offline"
            params["prompt"] = "select_account"

        elif provider == OIDCProvider.AZURE.value:
            # Azure AD specific: request v2.0 endpoint features
            params["response_mode"] = "query"

        # Build URL
        authorization_endpoint = provider_settings.authorization_endpoint
        return f"{authorization_endpoint}?{urlencode(params)}"

    async def exchange_code_for_tokens(
        self,
        provider: str,
        code: str,
        redirect_uri: str,
        code_verifier: str,
    ) -> OIDCTokens:
        """
        Exchange authorization code for tokens using PKCE.

        Args:
            provider: OIDC provider name
            code: Authorization code from callback
            redirect_uri: OAuth callback URL (must match authorization request)
            code_verifier: PKCE code verifier

        Returns:
            OIDCTokens containing access_token, id_token, etc.

        Raises:
            AuthenticationException: If token exchange fails
        """
        provider_settings = self._get_provider_settings(provider)

        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
            "client_id": provider_settings.client_id,
            "client_secret": provider_settings.client_secret,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    provider_settings.token_endpoint,
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30.0,
                )

                if response.status_code != 200:
                    error_data = response.json() if response.content else {}
                    error_msg = error_data.get("error_description", error_data.get("error", "Token exchange failed"))
                    logger.warning(
                        f"OIDC token exchange failed for provider {provider}: {error_msg}"
                    )
                    raise AuthenticationException(
                        f"Token exchange failed: {error_msg}",
                        {"provider": provider, "error": error_data},
                    )

                token_response = response.json()

        except httpx.RequestError as e:
            logger.error(f"Network error during token exchange: {e}")
            raise AuthenticationException(
                "Failed to connect to identity provider",
                {"provider": provider, "error": str(e)},
            )

        # Extract tokens
        if "id_token" not in token_response:
            raise AuthenticationException(
                "ID token not returned by provider",
                {"provider": provider},
            )

        return OIDCTokens(
            access_token=token_response["access_token"],
            id_token=token_response["id_token"],
            refresh_token=token_response.get("refresh_token"),
            token_type=token_response.get("token_type", "Bearer"),
            expires_in=token_response.get("expires_in"),
            scope=token_response.get("scope"),
        )

    async def _fetch_jwks(self, provider: str) -> Dict[str, Any]:
        """
        Fetch and cache JWKS (JSON Web Key Set) for token validation.

        Args:
            provider: OIDC provider name

        Returns:
            JWKS data

        Raises:
            AuthenticationException: If JWKS fetch fails
        """
        # Return cached JWKS if available
        if provider in self._jwks_cache:
            return self._jwks_cache[provider]

        provider_settings = self._get_provider_settings(provider)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    provider_settings.jwks_uri,
                    timeout=30.0,
                )

                if response.status_code != 200:
                    raise AuthenticationException(
                        "Failed to fetch JWKS from identity provider",
                        {"provider": provider, "status": response.status_code},
                    )

                jwks = response.json()
                self._jwks_cache[provider] = jwks
                return jwks

        except httpx.RequestError as e:
            logger.error(f"Failed to fetch JWKS for {provider}: {e}")
            raise AuthenticationException(
                "Failed to fetch signing keys from identity provider",
                {"provider": provider, "error": str(e)},
            )

    async def validate_id_token(
        self,
        provider: str,
        id_token: str,
        nonce: str,
        client_id: Optional[str] = None,
    ) -> OIDCUserInfo:
        """
        Validate ID token and extract user information.

        Performs full validation:
        - Signature verification using provider's JWKS
        - Issuer (iss) claim validation
        - Audience (aud) claim validation
        - Expiration (exp) claim validation
        - Nonce validation for replay protection

        Args:
            provider: OIDC provider name
            id_token: The ID token to validate
            nonce: Expected nonce value
            client_id: Optional client ID override for audience validation

        Returns:
            OIDCUserInfo with extracted claims

        Raises:
            AuthenticationException: If token validation fails
        """
        provider_settings = self._get_provider_settings(provider)

        # Get expected values
        expected_issuer = provider_settings.issuer
        expected_audience = client_id or provider_settings.client_id

        # Fetch JWKS for signature validation
        jwks_data = await self._fetch_jwks(provider)

        try:
            # Import JWKS
            jwks = JsonWebKey.import_key_set(jwks_data)

            # Decode and validate the token
            claims = jwt.decode(
                id_token,
                jwks,
                claims_options={
                    "iss": {"essential": True, "value": expected_issuer},
                    "aud": {"essential": True, "value": expected_audience},
                    "exp": {"essential": True},
                    "iat": {"essential": True},
                    "sub": {"essential": True},
                },
            )

            # Validate claims
            claims.validate()

            # Validate nonce
            token_nonce = claims.get("nonce")
            if token_nonce != nonce:
                raise AuthenticationException(
                    "ID token nonce mismatch - possible replay attack",
                    {"provider": provider},
                )

        except JoseError as e:
            logger.warning(f"ID token validation failed for {provider}: {e}")
            raise AuthenticationException(
                f"ID token validation failed: {str(e)}",
                {"provider": provider},
            )

        # Extract user info from claims
        return OIDCUserInfo(
            sub=claims["sub"],
            email=claims.get("email", ""),
            email_verified=claims.get("email_verified", False),
            name=claims.get("name"),
            given_name=claims.get("given_name"),
            family_name=claims.get("family_name"),
            picture=claims.get("picture"),
            groups=self._extract_groups(provider, claims),
            raw_claims=dict(claims),
        )

    def _extract_groups(self, provider: str, claims: Dict[str, Any]) -> Optional[list]:
        """
        Extract group memberships from ID token claims.

        Different providers use different claim names for groups:
        - Okta: 'groups' (requires groups claim configuration)
        - Azure AD: 'groups' (Object IDs) or 'roles'
        - Google: No standard groups claim (requires directory API)

        Args:
            provider: OIDC provider name
            claims: Token claims

        Returns:
            List of group names/IDs or None if not present
        """
        # Try common group claim names
        group_claim_names = ["groups", "roles", "group", "memberOf"]

        for claim_name in group_claim_names:
            if claim_name in claims:
                groups = claims[claim_name]
                if isinstance(groups, list):
                    return groups
                elif isinstance(groups, str):
                    return [groups]

        return None

    async def get_userinfo(self, provider: str, access_token: str) -> Dict[str, Any]:
        """
        Fetch user information from the userinfo endpoint.

        This can provide additional claims not included in the ID token.

        Args:
            provider: OIDC provider name
            access_token: Valid access token

        Returns:
            UserInfo response as dictionary

        Raises:
            AuthenticationException: If userinfo fetch fails
        """
        provider_settings = self._get_provider_settings(provider)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    provider_settings.userinfo_endpoint,
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=30.0,
                )

                if response.status_code != 200:
                    logger.warning(
                        f"UserInfo fetch failed for {provider}: {response.status_code}"
                    )
                    raise AuthenticationException(
                        "Failed to fetch user information",
                        {"provider": provider, "status": response.status_code},
                    )

                return response.json()

        except httpx.RequestError as e:
            logger.error(f"Network error fetching userinfo: {e}")
            raise AuthenticationException(
                "Failed to connect to identity provider",
                {"provider": provider, "error": str(e)},
            )

    async def authenticate(
        self,
        provider: str,
        code: str,
        redirect_uri: str,
        code_verifier: str,
        state: str,
        expected_state: str,
        nonce: str,
    ) -> OIDCUserInfo:
        """
        Complete OIDC authentication flow.

        This is a convenience method that performs the full authentication:
        1. Validate state parameter (CSRF protection)
        2. Exchange authorization code for tokens
        3. Validate ID token
        4. Extract and return user information

        Args:
            provider: OIDC provider name
            code: Authorization code from callback
            redirect_uri: OAuth callback URL
            code_verifier: PKCE code verifier
            state: State from callback
            expected_state: Expected state value (from session)
            nonce: Expected nonce value (from session)

        Returns:
            OIDCUserInfo with authenticated user details

        Raises:
            ValidationException: If state validation fails
            AuthenticationException: If authentication fails
        """
        # Validate state (CSRF protection)
        if state != expected_state:
            logger.warning(f"State mismatch during OIDC callback for {provider}")
            raise ValidationException(
                "Invalid state parameter - possible CSRF attack",
                {"provider": provider},
            )

        # Exchange code for tokens
        tokens = await self.exchange_code_for_tokens(
            provider=provider,
            code=code,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier,
        )

        # Validate ID token and extract user info
        user_info = await self.validate_id_token(
            provider=provider,
            id_token=tokens.id_token,
            nonce=nonce,
        )

        logger.info(
            f"OIDC authentication successful for {user_info.email} via {provider}"
        )

        return user_info

    def clear_jwks_cache(self, provider: Optional[str] = None) -> None:
        """
        Clear cached JWKS data.

        Args:
            provider: Optional provider to clear cache for. If None, clears all.
        """
        if provider:
            self._jwks_cache.pop(provider, None)
        else:
            self._jwks_cache.clear()


# Singleton instance
_oidc_service: Optional[OIDCService] = None


def get_oidc_service() -> OIDCService:
    """Get or create OIDC service singleton"""
    global _oidc_service
    if _oidc_service is None:
        _oidc_service = OIDCService()
    return _oidc_service
