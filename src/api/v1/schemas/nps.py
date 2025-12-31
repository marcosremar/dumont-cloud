"""
NPS (Net Promoter Score) API Schemas (Pydantic models)
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


# ============== Request Schemas ==============


class NPSSubmissionRequest(BaseModel):
    """NPS survey submission request"""
    score: int = Field(..., ge=0, le=10, description="NPS score (0-10)")
    comment: Optional[str] = Field(None, max_length=2000, description="Optional feedback comment")
    trigger_type: str = Field(..., min_length=1, max_length=50, description="Survey trigger type (first_deployment, monthly, issue_resolution)")

    @field_validator('trigger_type')
    @classmethod
    def validate_trigger_type(cls, v: str) -> str:
        """Validate trigger type is one of the allowed values"""
        allowed_types = ['first_deployment', 'monthly', 'issue_resolution']
        if v not in allowed_types:
            raise ValueError(f"trigger_type must be one of: {', '.join(allowed_types)}")
        return v

    @field_validator('comment')
    @classmethod
    def sanitize_comment(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize comment to remove potentially harmful content"""
        if v is None:
            return None
        # Strip leading/trailing whitespace
        v = v.strip()
        # Return None if empty after stripping
        if not v:
            return None
        return v


class NPSDismissRequest(BaseModel):
    """NPS survey dismissal request"""
    trigger_type: str = Field(..., min_length=1, max_length=50, description="Survey trigger type")
    reason: Optional[str] = Field(None, max_length=500, description="Optional dismissal reason")


# ============== Response Schemas ==============


class NPSSubmissionResponse(BaseModel):
    """NPS survey submission response"""
    success: bool = Field(True, description="Submission success status")
    id: int = Field(..., description="Created NPS response ID")
    category: str = Field(..., description="NPS category (detractor, passive, promoter)")
    message: Optional[str] = Field(None, description="Success message")


class NPSShouldShowResponse(BaseModel):
    """Check if NPS survey should be shown to user"""
    should_show: bool = Field(..., description="Whether to show the survey")
    reason: str = Field(..., description="Reason for the decision")
    trigger_type: Optional[str] = Field(None, description="Suggested trigger type if should_show is true")
    survey_config: Optional[Dict[str, Any]] = Field(None, description="Survey configuration if available")


class NPSScoreDataPoint(BaseModel):
    """Single data point for NPS trend chart"""
    date: str = Field(..., description="Date in ISO format (YYYY-MM-DD)")
    nps_score: float = Field(..., description="Calculated NPS score for this period")
    total_responses: int = Field(..., description="Total responses in this period")
    detractors: int = Field(..., description="Number of detractors (0-6)")
    passives: int = Field(..., description="Number of passives (7-8)")
    promoters: int = Field(..., description="Number of promoters (9-10)")


class NPSCategoryBreakdown(BaseModel):
    """NPS category breakdown"""
    detractors: int = Field(0, description="Count of detractor responses (score 0-6)")
    passives: int = Field(0, description="Count of passive responses (score 7-8)")
    promoters: int = Field(0, description="Count of promoter responses (score 9-10)")
    detractors_percentage: float = Field(0, description="Percentage of detractors")
    passives_percentage: float = Field(0, description="Percentage of passives")
    promoters_percentage: float = Field(0, description="Percentage of promoters")


class NPSTrendsResponse(BaseModel):
    """NPS trends response for admin dashboard"""
    scores: List[NPSScoreDataPoint] = Field(default_factory=list, description="NPS score data points over time")
    categories: NPSCategoryBreakdown = Field(..., description="Overall category breakdown")
    current_nps: float = Field(..., description="Current overall NPS score (-100 to 100)")
    total_responses: int = Field(..., description="Total number of responses")
    average_score: float = Field(..., description="Average score (0-10)")
    start_date: Optional[str] = Field(None, description="Start date of the trends period")
    end_date: Optional[str] = Field(None, description="End date of the trends period")


class NPSDetractorItem(BaseModel):
    """Individual detractor response item"""
    id: int = Field(..., description="Response ID")
    user_id: str = Field(..., description="User ID")
    score: int = Field(..., description="NPS score (0-6 for detractors)")
    comment: Optional[str] = Field(None, description="User comment")
    trigger_type: str = Field(..., description="Survey trigger type")
    needs_followup: bool = Field(False, description="Whether follow-up is needed")
    followup_completed: bool = Field(False, description="Whether follow-up has been completed")
    followup_notes: Optional[str] = Field(None, description="Follow-up notes")
    created_at: str = Field(..., description="Response creation timestamp")


class NPSDetractorsResponse(BaseModel):
    """List of detractor responses for follow-up"""
    detractors: List[NPSDetractorItem] = Field(default_factory=list, description="List of detractor responses")
    count: int = Field(..., description="Total number of detractors")
    pending_followup: int = Field(0, description="Number of detractors needing follow-up")


class NPSResponseItem(BaseModel):
    """Individual NPS response item"""
    id: int = Field(..., description="Response ID")
    user_id: str = Field(..., description="User ID")
    score: int = Field(..., description="NPS score (0-10)")
    comment: Optional[str] = Field(None, description="User comment")
    trigger_type: str = Field(..., description="Survey trigger type")
    category: str = Field(..., description="NPS category")
    created_at: str = Field(..., description="Response creation timestamp")


class NPSListResponse(BaseModel):
    """List of NPS responses"""
    responses: List[NPSResponseItem] = Field(default_factory=list, description="List of NPS responses")
    count: int = Field(..., description="Total number of responses")


class NPSConfigItem(BaseModel):
    """NPS survey configuration item"""
    id: int = Field(..., description="Config ID")
    trigger_type: str = Field(..., description="Survey trigger type")
    enabled: bool = Field(True, description="Whether this trigger is enabled")
    frequency_days: int = Field(30, description="Minimum days between surveys")
    title: Optional[str] = Field(None, description="Custom survey title")
    description: Optional[str] = Field(None, description="Custom survey description")


class NPSConfigListResponse(BaseModel):
    """List of NPS survey configurations"""
    configs: List[NPSConfigItem] = Field(default_factory=list, description="List of configurations")
    count: int = Field(..., description="Total number of configurations")


class NPSFollowupUpdateRequest(BaseModel):
    """Update follow-up status for a detractor"""
    followup_completed: bool = Field(..., description="Whether follow-up has been completed")
    followup_notes: Optional[str] = Field(None, max_length=2000, description="Notes from the follow-up")


class NPSFollowupUpdateResponse(BaseModel):
    """Response after updating follow-up status"""
    success: bool = Field(True, description="Update success status")
    id: int = Field(..., description="Updated NPS response ID")
    message: Optional[str] = Field(None, description="Success message")


class NPSErrorResponse(BaseModel):
    """Error response for NPS operations"""
    error: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")
