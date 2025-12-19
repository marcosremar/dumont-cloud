"""
Fine-Tuning API endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks

from ..schemas.request import CreateFineTuneJobRequest
from ..schemas.response import (
    FineTuneJobResponse,
    ListFineTuneJobsResponse,
    FineTuneJobLogsResponse,
    FineTuneModelsResponse,
    SuccessResponse,
)
from ....domain.services.finetune_service import FineTuningService, get_finetune_service
from ..dependencies import require_auth, get_current_user_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/finetune", tags=["Fine-Tuning"], dependencies=[Depends(require_auth)])


def get_service() -> FineTuningService:
    """Dependency to get fine-tuning service"""
    return get_finetune_service()


@router.get("/models", response_model=FineTuneModelsResponse)
async def list_supported_models(
    service: FineTuningService = Depends(get_service),
):
    """
    List supported base models for fine-tuning.

    Returns list of Unsloth-compatible models with their requirements.
    """
    return FineTuneModelsResponse(models=service.get_supported_models())


@router.get("/jobs", response_model=ListFineTuneJobsResponse)
async def list_jobs(
    user_id: str = Depends(get_current_user_email),
    service: FineTuningService = Depends(get_service),
):
    """
    List all fine-tuning jobs for the current user.

    Returns jobs sorted by creation date (newest first).
    """
    jobs = service.list_jobs(user_id)
    job_responses = [FineTuneJobResponse.from_domain(job) for job in jobs]
    return ListFineTuneJobsResponse(jobs=job_responses, count=len(job_responses))


@router.post("/jobs", response_model=FineTuneJobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    request: CreateFineTuneJobRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_email),
    service: FineTuningService = Depends(get_service),
):
    """
    Create a new fine-tuning job.

    The job will be queued and started in the background.
    Use GET /jobs/{job_id} to check status.
    """
    try:
        # Create job
        job = service.create_job(
            user_id=user_id,
            name=request.name,
            base_model=request.base_model,
            dataset_source=request.dataset_source,
            dataset_path=request.dataset_path,
            dataset_format=request.dataset_format,
            config=request.config.model_dump() if request.config else None,
            gpu_type=request.gpu_type,
            num_gpus=request.num_gpus,
        )

        # Start job in background
        background_tasks.add_task(service.start_job, job.id)

        logger.info(f"Created fine-tuning job {job.id} for user {user_id}")
        return FineTuneJobResponse.from_domain(job)

    except Exception as e:
        logger.error(f"Failed to create fine-tuning job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/jobs/upload-dataset")
async def upload_dataset(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_email),
    service: FineTuningService = Depends(get_service),
):
    """
    Upload a dataset file for fine-tuning.

    Supports JSON and JSONL files in Alpaca or ShareGPT format.
    Returns the path to use when creating a fine-tuning job.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )

    if not file.filename.endswith(('.json', '.jsonl')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JSON and JSONL files are supported"
        )

    try:
        dataset_path = await service.upload_dataset(user_id, file)
        logger.info(f"Uploaded dataset for user {user_id}: {dataset_path}")
        return {"success": True, "dataset_path": dataset_path}

    except Exception as e:
        logger.error(f"Failed to upload dataset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/jobs/{job_id}", response_model=FineTuneJobResponse)
async def get_job(
    job_id: str,
    refresh: bool = False,
    user_id: str = Depends(get_current_user_email),
    service: FineTuningService = Depends(get_service),
):
    """
    Get fine-tuning job details.

    Set refresh=true to fetch latest status from SkyPilot.
    """
    if refresh:
        job = service.refresh_job_status(job_id)
    else:
        job = service.get_job(job_id, user_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    return FineTuneJobResponse.from_domain(job)


@router.get("/jobs/{job_id}/logs", response_model=FineTuneJobLogsResponse)
async def get_job_logs(
    job_id: str,
    tail: int = 100,
    user_id: str = Depends(get_current_user_email),
    service: FineTuningService = Depends(get_service),
):
    """
    Get logs from a fine-tuning job.

    Returns the last N lines of logs (default 100).
    """
    job = service.get_job(job_id, user_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    logs = service.get_job_logs(job_id, tail)
    return FineTuneJobLogsResponse(job_id=job_id, logs=logs)


@router.post("/jobs/{job_id}/cancel", response_model=SuccessResponse)
async def cancel_job(
    job_id: str,
    user_id: str = Depends(get_current_user_email),
    service: FineTuningService = Depends(get_service),
):
    """
    Cancel a running fine-tuning job.
    """
    success = service.cancel_job(job_id, user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to cancel job. Job may not exist or is not running."
        )

    logger.info(f"Cancelled fine-tuning job {job_id}")
    return SuccessResponse(success=True, message=f"Job {job_id} cancelled")


@router.post("/jobs/{job_id}/refresh", response_model=FineTuneJobResponse)
async def refresh_job_status(
    job_id: str,
    user_id: str = Depends(get_current_user_email),
    service: FineTuningService = Depends(get_service),
):
    """
    Refresh job status from SkyPilot.

    Fetches the latest status from SkyPilot and updates the job record.
    """
    job = service.refresh_job_status(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    return FineTuneJobResponse.from_domain(job)
