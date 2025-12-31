"""
OIDC (OpenID Connect) Authentication API endpoints
Handles OAuth 2.0 authorization code flow with PKCE for enterprise SSO
"""
import logging
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel, Field

from ....domain.services.oidc_service import OIDCService, get_oidc_service, OIDCProvider
from ....core.sso_config import get_sso_settings
from ....core.exceptions import ConfigurationException, AuthenticationException, ValidationException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/oidc", tags=["OIDC Authentication"])


# Request/Response Schemas

class OIDCLoginRequest(BaseModel):
    """OIDC login initiation request"""
    provider: str = Field(..., description="OIDC provider name (okta, azure, google)")
    login_hint: Optional[str] = Field(None, description="Optional email hint for pre-filling login form")
    redirect_uri: Optional[str] = Field(None, description="Optional custom redirect URI after login")


class OIDCLoginResponse(BaseModel):
    """OIDC login response (used for JSON response mode)"""
    authorization_url: str = Field(..., description="URL to redirect user to for authentication")
    state: str = Field(..., description="State parameter for CSRF protection")


class OIDCProvidersResponse(BaseModel):
    """Available OIDC providers response"""
    providers: list = Field(..., description="List of configured OIDC providers")


class OIDCAuthStateResponse(BaseModel):
    """OIDC auth state check response"""
    state: str = Field(..., description="State parameter")
    valid: bool = Field(..., description="Whether the state is valid and not expired")
    provider: Optional[str] = Field(None, description="Provider associated with this state")


# In-memory store for OIDC auth state (PKCE, nonce, etc.)
# In production, this should be Redis or another distributed cache
@dataclass
class OIDCAuthState:
    """Stores OIDC authentication state between login and callback"""
    provider: str
    code_verifier: str
    code_challenge: str
    nonce: str
    state: str
    redirect_uri: str
    created_at: float = field(default_factory=time.time)
    login_hint: Optional[str] = None
    custom_redirect: Optional[str] = None

    def is_expired(self, ttl_seconds: int = 600) -> bool:
        """Check if auth state has expired (default 10 minutes)"""
        return time.time() - self.created_at > ttl_seconds


class OIDCAuthStateStore:
    """
    In-memory store for OIDC authentication state.

    Note: This is suitable for single-instance deployments.
    For production multi-instance deployments, replace with Redis.
    """

    # Auth state TTL in seconds (10 minutes)
    STATE_TTL = 600

    # Maximum stored states (prevent memory exhaustion)
    MAX_STATES = 10000

    def __init__(self):
        self._states: Dict[str, OIDCAuthState] = {}

    def store(self, state: str, auth_state: OIDCAuthState) -> None:
        """Store auth state keyed by state parameter"""
        # Clean up expired states periodically
        self._cleanup_expired()

        if len(self._states) >= self.MAX_STATES:
            logger.warning("OIDC auth state store is full, cleaning up oldest entries")
            self._cleanup_oldest(self.MAX_STATES // 2)

        self._states[state] = auth_state
        logger.debug(f"Stored OIDC auth state for provider {auth_state.provider}")

    def get(self, state: str) -> Optional[OIDCAuthState]:
        """Retrieve auth state by state parameter"""
        auth_state = self._states.get(state)

        if auth_state is None:
            return None

        if auth_state.is_expired(self.STATE_TTL):
            del self._states[state]
            return None

        return auth_state

    def consume(self, state: str) -> Optional[OIDCAuthState]:
        """Retrieve and remove auth state (one-time use)"""
        auth_state = self.get(state)
        if auth_state:
            del self._states[state]
        return auth_state

    def _cleanup_expired(self) -> None:
        """Remove expired states"""
        now = time.time()
        expired_keys = [
            key for key, state in self._states.items()
            if state.is_expired(self.STATE_TTL)
        ]
        for key in expired_keys:
            del self._states[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired OIDC auth states")

    def _cleanup_oldest(self, keep_count: int) -> None:
        """Keep only the newest N states"""
        if len(self._states) <= keep_count:
            return

        # Sort by created_at and keep newest
        sorted_states = sorted(
            self._states.items(),
            key=lambda x: x[1].created_at,
            reverse=True
        )
        self._states = dict(sorted_states[:keep_count])


# Global auth state store instance
_auth_state_store: Optional[OIDCAuthStateStore] = None


def get_auth_state_store() -> OIDCAuthStateStore:
    """Get or create auth state store singleton"""
    global _auth_state_store
    if _auth_state_store is None:
        _auth_state_store = OIDCAuthStateStore()
    return _auth_state_store


# Dependency injection
def get_oidc_service_dependency() -> OIDCService:
    """Get OIDC service instance"""
    return get_oidc_service()


# API Endpoints

@router.get("/providers", response_model=OIDCProvidersResponse)
async def list_providers(
    oidc_service: OIDCService = Depends(get_oidc_service_dependency),
):
    """
    List configured OIDC providers

    Returns a list of OIDC providers that are properly configured
    and available for authentication.
    """
    providers = oidc_service.get_configured_providers()
    return OIDCProvidersResponse(providers=providers)


@router.post("/login", status_code=status.HTTP_302_FOUND)
async def initiate_oidc_login(
    request: OIDCLoginRequest,
    oidc_service: OIDCService = Depends(get_oidc_service_dependency),
    auth_state_store: OIDCAuthStateStore = Depends(get_auth_state_store),
):
    """
    Initiate OIDC login flow

    Initiates the OAuth 2.0 authorization code flow with PKCE.
    This endpoint:
    1. Validates the requested provider is configured
    2. Generates PKCE code verifier and challenge
    3. Generates state (CSRF protection) and nonce (replay protection)
    4. Stores auth state for callback validation
    5. Redirects to the Identity Provider's authorization endpoint

    Returns:
        302 redirect to the IdP authorization URL
    """
    provider = request.provider.lower()

    # Validate provider is configured
    if not oidc_service.is_provider_configured(provider):
        configured = oidc_service.get_configured_providers()
        logger.warning(
            f"OIDC login attempt for unconfigured provider: {provider}. "
            f"Configured providers: {configured}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider '{provider}' is not configured. Available providers: {configured}",
        )

    # Get SSO settings for callback URL
    sso_settings = get_sso_settings()
    redirect_uri = request.redirect_uri or sso_settings.general.callback_url

    # Generate PKCE pair
    code_verifier, code_challenge = oidc_service.generate_pkce_pair()

    # Generate state (CSRF protection)
    state = oidc_service.generate_state()

    # Generate nonce (ID token replay protection)
    nonce = oidc_service.generate_nonce()

    # Store auth state for callback validation
    auth_state = OIDCAuthState(
        provider=provider,
        code_verifier=code_verifier,
        code_challenge=code_challenge,
        nonce=nonce,
        state=state,
        redirect_uri=redirect_uri,
        login_hint=request.login_hint,
        custom_redirect=request.redirect_uri,
    )
    auth_state_store.store(state, auth_state)

    # Build authorization URL
    try:
        authorization_url = oidc_service.build_authorization_url(
            provider=provider,
            redirect_uri=redirect_uri,
            state=state,
            nonce=nonce,
            code_challenge=code_challenge,
            login_hint=request.login_hint,
        )
    except ConfigurationException as e:
        logger.error(f"Failed to build authorization URL for {provider}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to configure OIDC for provider {provider}",
        )

    logger.info(f"Initiating OIDC login flow for provider {provider}")

    # Return redirect to IdP
    return RedirectResponse(
        url=authorization_url,
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/login/json", response_model=OIDCLoginResponse)
async def initiate_oidc_login_json(
    request: OIDCLoginRequest,
    oidc_service: OIDCService = Depends(get_oidc_service_dependency),
    auth_state_store: OIDCAuthStateStore = Depends(get_auth_state_store),
):
    """
    Initiate OIDC login flow (JSON response)

    Same as /login but returns the authorization URL in a JSON response
    instead of redirecting. Useful for SPA frontends that need to handle
    the redirect themselves.

    Returns:
        JSON with authorization_url and state
    """
    provider = request.provider.lower()

    # Validate provider is configured
    if not oidc_service.is_provider_configured(provider):
        configured = oidc_service.get_configured_providers()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider '{provider}' is not configured. Available providers: {configured}",
        )

    # Get SSO settings for callback URL
    sso_settings = get_sso_settings()
    redirect_uri = request.redirect_uri or sso_settings.general.callback_url

    # Generate PKCE pair
    code_verifier, code_challenge = oidc_service.generate_pkce_pair()

    # Generate state and nonce
    state = oidc_service.generate_state()
    nonce = oidc_service.generate_nonce()

    # Store auth state
    auth_state = OIDCAuthState(
        provider=provider,
        code_verifier=code_verifier,
        code_challenge=code_challenge,
        nonce=nonce,
        state=state,
        redirect_uri=redirect_uri,
        login_hint=request.login_hint,
        custom_redirect=request.redirect_uri,
    )
    auth_state_store.store(state, auth_state)

    # Build authorization URL
    try:
        authorization_url = oidc_service.build_authorization_url(
            provider=provider,
            redirect_uri=redirect_uri,
            state=state,
            nonce=nonce,
            code_challenge=code_challenge,
            login_hint=request.login_hint,
        )
    except ConfigurationException as e:
        logger.error(f"Failed to build authorization URL for {provider}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to configure OIDC for provider {provider}",
        )

    logger.info(f"Initiating OIDC login flow for provider {provider} (JSON mode)")

    return OIDCLoginResponse(
        authorization_url=authorization_url,
        state=state,
    )


@router.get("/state/{state}", response_model=OIDCAuthStateResponse)
async def check_auth_state(
    state: str,
    auth_state_store: OIDCAuthStateStore = Depends(get_auth_state_store),
):
    """
    Check if an OIDC auth state is valid

    This endpoint is useful for debugging and verifying that the
    state parameter from a callback is valid before processing.

    Note: This does NOT consume the state - use the callback endpoint for that.
    """
    auth_state = auth_state_store.get(state)

    if auth_state is None:
        return OIDCAuthStateResponse(
            state=state,
            valid=False,
            provider=None,
        )

    return OIDCAuthStateResponse(
        state=state,
        valid=True,
        provider=auth_state.provider,
    )
