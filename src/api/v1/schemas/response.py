"""
API Response Schemas (Pydantic models)
"""
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


# Generic Responses

class SuccessResponse(BaseModel):
    """Generic success response"""
    success: bool = Field(True, description="Operation success status")
    message: Optional[str] = Field(None, description="Success message")


class ErrorResponse(BaseModel):
    """Generic error response"""
    error: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")


# Auth Responses

class LoginResponse(BaseModel):
    """Login response"""
    success: bool = Field(True, description="Login success")
    user: str = Field(..., description="User email")
    token: Optional[str] = Field(None, description="Session token")


class AuthMeResponse(BaseModel):
    """Auth me response"""
    authenticated: bool = Field(..., description="Authentication status")
    user: Optional[Dict[str, Any]] = Field(None, description="User data if authenticated")


# GPU Offer Responses

class GpuOfferResponse(BaseModel):
    """GPU offer response"""
    id: int
    gpu_name: str
    num_gpus: int
    gpu_ram: float
    cpu_cores: int
    cpu_ram: float
    disk_space: float
    inet_down: float
    inet_up: float
    dph_total: float
    geolocation: Optional[str] = None
    reliability: float
    cuda_version: Optional[str] = None
    verified: bool
    static_ip: bool

    # Machine History fields (from blacklist/history system)
    machine_id: Optional[str] = None
    is_blacklisted: bool = False
    blacklist_reason: Optional[str] = None
    success_rate: Optional[float] = None  # 0.0 to 1.0
    total_attempts: int = 0
    reliability_status: Optional[str] = None  # excellent, good, fair, poor, unknown

    @field_validator('cuda_version', mode='before')
    @classmethod
    def convert_cuda_version(cls, v):
        """Convert cuda_version to string if it's a float"""
        if v is None:
            return "0.0"
        return str(v)


class SearchOffersResponse(BaseModel):
    """Search offers response"""
    offers: List[GpuOfferResponse]
    count: int = Field(..., description="Number of offers found")


# CPU Standby Info

class CPUStandbyInfo(BaseModel):
    """CPU Standby information"""
    enabled: bool = False
    provider: str = "gcp"  # gcp, aws, etc
    name: Optional[str] = None
    zone: Optional[str] = None
    ip: Optional[str] = None
    machine_type: Optional[str] = None
    status: Optional[str] = None  # running, stopped, etc
    dph_total: float = 0.0  # Cost per hour
    sync_enabled: bool = False
    sync_count: int = 0
    state: Optional[str] = None  # syncing, ready, failover_active


# Instance Responses

class InstanceResponse(BaseModel):
    """Instance response"""
    id: int
    status: str
    actual_status: Optional[str] = None  # Can be None when instance is starting
    gpu_name: str
    num_gpus: int
    gpu_ram: float
    cpu_cores: int
    cpu_ram: float
    disk_space: float
    dph_total: float
    public_ipaddr: Optional[str] = None
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = None
    start_date: Optional[str] = None
    label: Optional[str] = None
    ports: Optional[Dict[str, Any]] = None

    # Real-time metrics
    gpu_util: Optional[float] = None
    gpu_temp: Optional[float] = None
    cpu_util: Optional[float] = None
    ram_used: Optional[float] = None
    ram_total: Optional[float] = None

    # Provider info
    provider: str = "vast.ai"

    # CPU Standby info (for failover)
    cpu_standby: Optional[CPUStandbyInfo] = None

    # Combined cost (GPU + CPU standby)
    total_dph: Optional[float] = None


class ListInstancesResponse(BaseModel):
    """List instances response"""
    instances: List[InstanceResponse]
    count: int = Field(..., description="Number of instances")


# Snapshot Responses

class SnapshotResponse(BaseModel):
    """Snapshot response"""
    id: str
    short_id: str
    time: str
    hostname: str
    tags: List[str]
    paths: List[str]


class ListSnapshotsResponse(BaseModel):
    """List snapshots response"""
    snapshots: List[SnapshotResponse]
    count: int = Field(..., description="Number of snapshots")


class CreateSnapshotResponse(BaseModel):
    """Create snapshot response"""
    success: bool = True
    snapshot_id: str
    files_new: int
    files_changed: int
    files_unmodified: int
    total_files_processed: int
    data_added: int
    total_bytes_processed: int


class RestoreSnapshotResponse(BaseModel):
    """Restore snapshot response"""
    success: bool
    snapshot_id: str
    target_path: str
    files_restored: int
    errors: List[str]


class RetentionPolicyResponse(BaseModel):
    """Retention policy response"""
    retention_days: int = Field(..., description="Default retention days")
    min_snapshots_to_keep: int = Field(..., description="Minimum snapshots to keep")
    max_snapshots_per_instance: int = Field(..., description="Maximum snapshots per instance")
    cleanup_enabled: bool = Field(..., description="Whether automatic cleanup is enabled")
    instance_id: Optional[str] = Field(None, description="Instance ID (null for global policy)")
    is_instance_policy: bool = Field(False, description="Whether this is an instance-specific policy")


# Settings Responses

class SettingsResponse(BaseModel):
    """User settings response"""
    vast_api_key: Optional[str] = None
    settings: Dict[str, Any] = Field(default_factory=dict)


# Balance Response

class BalanceResponse(BaseModel):
    """Account balance response"""
    credit: float = Field(..., description="Account credit")
    balance: float = Field(..., description="Account balance")
    balance_threshold: float = Field(..., description="Balance threshold")
    email: str = Field(..., description="User email")


# Migration Responses

class MigrationResponse(BaseModel):
    """Migration result response"""
    success: bool = Field(..., description="Migration success status")
    new_instance_id: Optional[int] = Field(None, description="New instance ID")
    old_instance_id: Optional[int] = Field(None, description="Old instance ID")
    snapshot_id: Optional[str] = Field(None, description="Snapshot ID used")
    error: Optional[str] = Field(None, description="Error message if failed")
    steps_completed: List[str] = Field(default_factory=list, description="Steps completed")


class MigrationEstimateResponse(BaseModel):
    """Migration estimate response"""
    available: bool = Field(..., description="Migration available")
    error: Optional[str] = Field(None, description="Error if not available")
    source: Optional[Dict[str, Any]] = Field(None, description="Source instance info")
    target: Optional[Dict[str, Any]] = Field(None, description="Target type info")
    estimated_time_minutes: Optional[int] = Field(None, description="Estimated time")
    offers_available: Optional[int] = Field(None, description="Number of offers")


# Sync Responses

class SyncResponse(BaseModel):
    """Sync operation response"""
    success: bool = Field(..., description="Sync success status")
    instance_id: int = Field(..., description="Instance ID")
    snapshot_id: Optional[str] = Field(None, description="Snapshot ID created")
    files_new: int = Field(0, description="New files")
    files_changed: int = Field(0, description="Changed files")
    files_unmodified: int = Field(0, description="Unchanged files")
    data_added: str = Field("0 B", description="Data added (human readable)")
    data_added_bytes: int = Field(0, description="Data added in bytes")
    duration_seconds: float = Field(0, description="Duration in seconds")
    is_incremental: bool = Field(True, description="Was incremental sync")
    error: Optional[str] = Field(None, description="Error message if failed")


class SyncStatusResponse(BaseModel):
    """Sync status response"""
    instance_id: int = Field(..., description="Instance ID")
    synced: bool = Field(False, description="Has been synced")
    is_syncing: bool = Field(False, description="Currently syncing")
    last_sync: Optional[str] = Field(None, description="Last sync timestamp")
    last_sync_ago: str = Field("Never", description="Time since last sync")
    last_snapshot_id: Optional[str] = Field(None, description="Last snapshot ID")
    sync_count: int = Field(0, description="Total sync count")
    last_stats: Optional[Dict[str, Any]] = Field(None, description="Last sync statistics")
    error: Optional[str] = Field(None, description="Last error if any")


# Fine-Tuning Responses

class FineTuneJobResponse(BaseModel):
    """Fine-tuning job response"""
    id: str = Field(..., description="Job ID")
    user_id: str = Field(..., description="User ID")
    name: str = Field(..., description="Job name")
    status: str = Field(..., description="Job status")
    base_model: str = Field(..., description="Base model ID")
    dataset_source: str = Field(..., description="Dataset source")
    dataset_path: str = Field(..., description="Dataset path")
    dataset_format: str = Field(..., description="Dataset format")
    gpu_type: str = Field(..., description="GPU type")
    num_gpus: int = Field(..., description="Number of GPUs")
    config: Dict[str, Any] = Field(..., description="Fine-tuning config")

    # Progress
    current_epoch: int = Field(0, description="Current epoch")
    current_step: int = Field(0, description="Current step")
    total_steps: int = Field(0, description="Total steps")
    loss: Optional[float] = Field(None, description="Current loss")
    progress_percent: float = Field(0.0, description="Progress percentage")

    # Timestamps
    created_at: str = Field(..., description="Creation timestamp")
    started_at: Optional[str] = Field(None, description="Start timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")

    # Output
    output_model_path: Optional[str] = Field(None, description="Output model path")
    error_message: Optional[str] = Field(None, description="Error message if failed")

    @classmethod
    def from_domain(cls, job) -> "FineTuneJobResponse":
        """Create from domain model"""
        return cls(
            id=job.id,
            user_id=job.user_id,
            name=job.name,
            status=job.status.value,
            base_model=job.config.base_model,
            dataset_source=job.dataset_source.value,
            dataset_path=job.dataset_path,
            dataset_format=job.dataset_format,
            gpu_type=job.gpu_type,
            num_gpus=job.num_gpus,
            config=job.config.to_dict(),
            current_epoch=job.current_epoch,
            current_step=job.current_step,
            total_steps=job.total_steps,
            loss=job.loss,
            progress_percent=job.progress_percent,
            created_at=job.created_at.isoformat() if job.created_at else None,
            started_at=job.started_at.isoformat() if job.started_at else None,
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
            output_model_path=job.output_model_path,
            error_message=job.error_message,
        )


class ListFineTuneJobsResponse(BaseModel):
    """List fine-tuning jobs response"""
    jobs: List[FineTuneJobResponse] = Field(..., description="List of jobs")
    count: int = Field(..., description="Number of jobs")


class FineTuneJobLogsResponse(BaseModel):
    """Fine-tuning job logs response"""
    job_id: str = Field(..., description="Job ID")
    logs: str = Field(..., description="Log output")


class FineTuneModelsResponse(BaseModel):
    """Supported models response"""
    models: List[Dict[str, Any]] = Field(..., description="List of supported models")


# Reservation Responses

class ReservationResponse(BaseModel):
    """GPU reservation response"""
    id: int = Field(..., description="Reservation ID")
    user_id: str = Field(..., description="User ID")
    gpu_type: str = Field(..., description="GPU type (e.g., 'A100', 'H100')")
    gpu_count: int = Field(1, description="Number of GPUs")
    start_time: str = Field(..., description="Reservation start time (ISO 8601)")
    end_time: str = Field(..., description="Reservation end time (ISO 8601)")
    status: str = Field(..., description="Reservation status (pending, active, completed, cancelled, failed)")
    credits_used: float = Field(0.0, description="Credits used for this reservation")
    credits_refunded: float = Field(0.0, description="Credits refunded (if cancelled)")
    discount_rate: int = Field(15, description="Discount rate applied (10-20%)")
    spot_price_per_hour: Optional[float] = Field(None, description="Spot price at time of reservation")
    reserved_price_per_hour: Optional[float] = Field(None, description="Discounted reserved price")
    instance_id: Optional[str] = Field(None, description="Allocated instance ID (when active)")
    provider: Optional[str] = Field(None, description="GPU provider")
    duration_hours: float = Field(0.0, description="Reservation duration in hours")
    is_active: bool = Field(False, description="Whether reservation is currently active")
    is_upcoming: bool = Field(False, description="Whether reservation is scheduled for future")
    is_cancellable: bool = Field(False, description="Whether reservation can be cancelled")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")
    started_at: Optional[str] = Field(None, description="When reservation started")
    completed_at: Optional[str] = Field(None, description="When reservation completed")
    cancelled_at: Optional[str] = Field(None, description="When reservation was cancelled")
    cancellation_reason: Optional[str] = Field(None, description="Reason for cancellation")
    failure_reason: Optional[str] = Field(None, description="Reason for failure")

    @classmethod
    def from_model(cls, reservation) -> "ReservationResponse":
        """Create from SQLAlchemy model"""
        return cls(
            id=reservation.id,
            user_id=reservation.user_id,
            gpu_type=reservation.gpu_type,
            gpu_count=reservation.gpu_count,
            start_time=reservation.start_time.isoformat() if reservation.start_time else None,
            end_time=reservation.end_time.isoformat() if reservation.end_time else None,
            status=reservation.status.value if reservation.status else None,
            credits_used=reservation.credits_used or 0.0,
            credits_refunded=reservation.credits_refunded or 0.0,
            discount_rate=reservation.discount_rate or 15,
            spot_price_per_hour=reservation.spot_price_per_hour,
            reserved_price_per_hour=reservation.reserved_price_per_hour,
            instance_id=reservation.instance_id,
            provider=reservation.provider,
            duration_hours=reservation.duration_hours,
            is_active=reservation.is_active,
            is_upcoming=reservation.is_upcoming,
            is_cancellable=reservation.is_cancellable,
            created_at=reservation.created_at.isoformat() if reservation.created_at else None,
            updated_at=reservation.updated_at.isoformat() if reservation.updated_at else None,
            started_at=reservation.started_at.isoformat() if reservation.started_at else None,
            completed_at=reservation.completed_at.isoformat() if reservation.completed_at else None,
            cancelled_at=reservation.cancelled_at.isoformat() if reservation.cancelled_at else None,
            cancellation_reason=reservation.cancellation_reason,
            failure_reason=reservation.failure_reason,
        )


class ListReservationsResponse(BaseModel):
    """List reservations response"""
    reservations: List[ReservationResponse] = Field(..., description="List of reservations")
    count: int = Field(..., description="Number of reservations")


class AvailabilityResponse(BaseModel):
    """GPU availability check response"""
    available: bool = Field(..., description="Whether GPU is available for the requested time")
    gpu_type: str = Field(..., description="GPU type checked")
    gpu_count: int = Field(1, description="Number of GPUs requested")
    start_time: str = Field(..., description="Requested start time")
    end_time: str = Field(..., description="Requested end time")
    capacity: Optional[int] = Field(None, description="Available capacity (number of GPUs)")
    conflicting_reservations: int = Field(0, description="Number of conflicting reservations")
    message: Optional[str] = Field(None, description="Additional information")


class PricingEstimateResponse(BaseModel):
    """Reservation pricing estimate response"""
    gpu_type: str = Field(..., description="GPU type")
    gpu_count: int = Field(1, description="Number of GPUs")
    duration_hours: float = Field(..., description="Reservation duration in hours")
    spot_price_per_hour: float = Field(..., description="Current spot price per hour")
    discount_rate: int = Field(..., description="Discount rate (10-20%)")
    reserved_price_per_hour: float = Field(..., description="Discounted reserved price per hour")
    total_spot_cost: float = Field(..., description="Total cost at spot price")
    total_reserved_cost: float = Field(..., description="Total cost with reservation discount")
    savings: float = Field(..., description="Total savings with reservation")
    credits_required: float = Field(..., description="Credits required for reservation")


class CancelReservationResponse(BaseModel):
    """Cancel reservation response"""
    success: bool = Field(True, description="Cancellation success status")
    reservation_id: int = Field(..., description="Cancelled reservation ID")
    message: str = Field(..., description="Cancellation message")
    credits_refunded: float = Field(0.0, description="Credits refunded")
    refund_percentage: float = Field(0.0, description="Percentage of credits refunded")


class ReservationCreditResponse(BaseModel):
    """Reservation credit response"""
    id: int = Field(..., description="Credit ID")
    user_id: str = Field(..., description="User ID")
    amount: float = Field(..., description="Available credit amount")
    original_amount: float = Field(..., description="Original credit amount")
    status: str = Field(..., description="Credit status (available, locked, used, expired, refunded)")
    transaction_type: str = Field(..., description="Transaction type (purchase, deduction, refund, etc)")
    reservation_id: Optional[int] = Field(None, description="Associated reservation ID")
    expires_at: str = Field(..., description="Expiration timestamp")
    days_until_expiration: int = Field(..., description="Days until expiration (-1 if locked)")
    is_available: bool = Field(False, description="Whether credit is available for use")
    is_expired: bool = Field(False, description="Whether credit is expired")
    description: Optional[str] = Field(None, description="Credit description")
    created_at: str = Field(..., description="Creation timestamp")

    @classmethod
    def from_model(cls, credit) -> "ReservationCreditResponse":
        """Create from SQLAlchemy model"""
        return cls(
            id=credit.id,
            user_id=credit.user_id,
            amount=credit.amount,
            original_amount=credit.original_amount,
            status=credit.status.value if credit.status else None,
            transaction_type=credit.transaction_type.value if credit.transaction_type else None,
            reservation_id=credit.reservation_id,
            expires_at=credit.expires_at.isoformat() if credit.expires_at else None,
            days_until_expiration=credit.days_until_expiration,
            is_available=credit.is_available,
            is_expired=credit.is_expired,
            description=credit.description,
            created_at=credit.created_at.isoformat() if credit.created_at else None,
        )


class CreditBalanceResponse(BaseModel):
    """User credit balance response"""
    user_id: str = Field(..., description="User ID")
    available_credits: float = Field(0.0, description="Total available credits")
    locked_credits: float = Field(0.0, description="Credits locked in active reservations")
    total_credits: float = Field(0.0, description="Total credits (available + locked)")
    expiring_soon: float = Field(0.0, description="Credits expiring within 7 days")
    credits: List[ReservationCreditResponse] = Field(default_factory=list, description="Credit details")


class ListCreditsResponse(BaseModel):
    """List credits response"""
    credits: List[ReservationCreditResponse] = Field(..., description="List of credits")
    count: int = Field(..., description="Number of credits")
