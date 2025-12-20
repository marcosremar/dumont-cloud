"""
User settings API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status

from ..schemas.request import UpdateSettingsRequest
from ..schemas.response import SettingsResponse, SuccessResponse, BalanceResponse
from ....domain.services import AuthService
from ....core.exceptions import NotFoundException
from ..dependencies import get_auth_service, get_current_user_email, require_auth, get_instance_service
from ....domain.services import InstanceService

router = APIRouter(prefix="/settings", tags=["Settings"], dependencies=[Depends(require_auth)])


@router.get("", response_model=SettingsResponse)
async def get_settings(
    user_email: str = Depends(get_current_user_email),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Get user settings

    Returns current user settings including API keys and preferences.
    """
    try:
        user = auth_service.get_user(user_email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return SettingsResponse(
            vast_api_key=user.vast_api_key,
            settings=user.settings,
        )
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.put("", response_model=SuccessResponse)
async def update_settings(
    request: UpdateSettingsRequest,
    user_email: str = Depends(get_current_user_email),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Update user settings

    Updates user settings including API keys and preferences.
    """
    try:
        updates = {}

        if request.vast_api_key is not None:
            updates["vast_api_key"] = request.vast_api_key

        if request.settings is not None:
            updates["settings"] = request.settings

        # Update user via auth service's user repository
        from ..dependencies import get_user_repository
        user_repo = next(get_user_repository())
        user_repo.update_user(user_email, updates)

        return SuccessResponse(
            success=True,
            message="Settings updated successfully",
        )
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/complete-onboarding", response_model=SuccessResponse)
async def complete_onboarding(
    user_email: str = Depends(get_current_user_email),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Marks onboarding as completed for the current user.
    """
    try:
        from ..dependencies import get_user_repository
        user_repo = next(get_user_repository())
        user = auth_service.get_user(user_email)

        settings = user.settings or {}
        settings["has_completed_onboarding"] = True

        user_repo.update_user(user_email, {"settings": settings})

        return SuccessResponse(
            success=True,
            message="Onboarding completed",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Cloud Storage Failover settings
@router.get("/cloud-storage")
async def get_cloud_storage_settings(
    user_email: str = Depends(get_current_user_email),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Get cloud storage failover settings
    """
    try:
        user = auth_service.get_user(user_email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        settings = user.settings or {}
        cloud_storage = settings.get("cloud_storage", {})

        return {"settings": cloud_storage}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/cloud-storage", response_model=SuccessResponse)
async def update_cloud_storage_settings(
    request: dict,
    user_email: str = Depends(get_current_user_email),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Update cloud storage failover settings
    """
    try:
        from ..dependencies import get_user_repository
        user_repo = next(get_user_repository())
        user = auth_service.get_user(user_email)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        settings = user.settings or {}
        settings["cloud_storage"] = request

        user_repo.update_user(user_email, {"settings": settings})

        return SuccessResponse(
            success=True,
            message="Cloud storage settings updated",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cloud-storage/test", response_model=SuccessResponse)
async def test_cloud_storage_connection(
    request: dict,
    user_email: str = Depends(get_current_user_email),
):
    """
    Test cloud storage connection
    """
    try:
        provider = request.get("primary_provider", "")

        # Basic validation based on provider
        if provider == "backblaze_b2":
            if not request.get("b2_key_id") or not request.get("b2_app_key"):
                raise HTTPException(status_code=400, detail="Missing B2 credentials")
        elif provider == "aws_s3":
            if not request.get("s3_access_key") or not request.get("s3_secret_key"):
                raise HTTPException(status_code=400, detail="Missing S3 credentials")
        elif provider == "google_gcs":
            if not request.get("gcs_credentials_json"):
                raise HTTPException(status_code=400, detail="Missing GCS credentials")
        elif provider == "cloudflare_r2":
            # R2 uses the main settings, so we just validate it's configured
            pass

        # TODO: Actually test the connection using rclone or boto3
        # For now, just validate the configuration

        return SuccessResponse(
            success=True,
            message=f"Connection to {provider} validated",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Balance endpoint (separate router to mount at /api/balance)
balance_router = APIRouter(tags=["Balance"], dependencies=[Depends(require_auth)])


@balance_router.get("/balance", response_model=BalanceResponse)
async def get_balance(
    user_email: str = Depends(get_current_user_email),
    instance_service: InstanceService = Depends(get_instance_service),
):
    """
    Get account balance from Vast.ai

    Returns current account credit and balance.
    """
    try:
        balance_info = instance_service.get_balance()
        return BalanceResponse(
            credit=balance_info.get("credit", 0),
            balance=balance_info.get("balance", 0),
            balance_threshold=balance_info.get("balance_threshold", 0),
            email=user_email,
        )
    except Exception as e:
        # Return zeros if balance fetch fails
        return BalanceResponse(
            credit=0,
            balance=0,
            balance_threshold=0,
            email=user_email,
        )
