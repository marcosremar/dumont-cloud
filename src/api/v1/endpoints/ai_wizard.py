"""
AI Wizard API Endpoint
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from src.services.ai_wizard_service import ai_wizard_service

router = APIRouter(prefix="/ai-wizard", tags=["AI Wizard"])


class Message(BaseModel):
    role: str = Field(..., description="Message role: user or assistant")
    content: str = Field(..., description="Message content")


class AnalyzeRequest(BaseModel):
    project_description: str = Field(..., description="User's project description")
    conversation_history: Optional[List[Message]] = Field(
        default=None,
        description="Previous conversation messages for context"
    )


class GPUOption(BaseModel):
    tier: str = Field(..., description="minima, recomendada, or maxima")
    gpu: str = Field(..., description="GPU model name")
    vram: str = Field(..., description="VRAM amount")
    price_per_hour: str = Field(..., description="Price per hour")
    frameworks: Optional[Dict[str, str]] = Field(default=None, description="Performance by framework")
    ram_offload: Optional[str] = Field(default=None, description="RAM offload requirements")
    tokens_per_second: Optional[str] = Field(default=None, description="Estimated tokens/second (legacy)")
    observation: str = Field(..., description="Additional notes")


class ModelInfo(BaseModel):
    name: str = Field(..., description="Model name")
    parameters: str = Field(..., description="Model size in parameters")
    vram_fp16: Optional[str] = Field(default=None, description="VRAM for FP16")
    vram_int8: Optional[str] = Field(default=None, description="VRAM for INT8")
    vram_int4: Optional[str] = Field(default=None, description="VRAM for INT4")
    vram_required: Optional[str] = Field(default=None, description="VRAM required (legacy)")
    recommended_quantization: Optional[str] = Field(default=None, description="Recommended quantization")
    quantization: Optional[str] = Field(default=None, description="Quantization (legacy)")


class GPURecommendation(BaseModel):
    workload_type: str
    model_info: Optional[ModelInfo] = None
    gpu_options: Optional[List[GPUOption]] = None
    optimization_tips: Optional[List[str]] = Field(default=None, description="Optimization tips")
    # Legacy fields for backward compatibility
    min_vram_gb: Optional[int] = None
    recommended_gpus: Optional[List[str]] = None
    tier_suggestion: Optional[str] = None
    explanation: str
    search_sources: Optional[str] = None


class AnalyzeResponse(BaseModel):
    success: bool
    needs_more_info: bool
    questions: List[str] = []
    recommendation: Optional[GPURecommendation] = None
    model_used: str


# Cost Optimization Models
class CostOptimizationRequest(BaseModel):
    user_id: str = Field(..., description="User identifier")
    instance_id: str = Field(..., description="Instance identifier")
    days_to_analyze: int = Field(
        default=30,
        ge=3,
        le=90,
        description="Number of days of historical data to analyze (3-90)"
    )
    current_hibernation_timeout: int = Field(
        default=0,
        ge=0,
        description="Current hibernation timeout in minutes (0 = disabled)"
    )


class RecommendationItem(BaseModel):
    type: str = Field(..., description="Recommendation type: gpu_downgrade, gpu_upgrade, hibernation, spot_timing")
    current_gpu: Optional[str] = Field(default=None, description="Current GPU type (for GPU recommendations)")
    recommended_gpu: Optional[str] = Field(default=None, description="Recommended GPU type (for GPU recommendations)")
    current_timeout_minutes: Optional[int] = Field(default=None, description="Current timeout (for hibernation)")
    recommended_timeout_minutes: Optional[int] = Field(default=None, description="Recommended timeout (for hibernation)")
    recommended_windows: Optional[List[Dict[str, str]]] = Field(default=None, description="Recommended timing windows (for spot)")
    reason: str = Field(..., description="Explanation for the recommendation")
    estimated_monthly_savings_usd: float = Field(..., description="Estimated monthly savings in USD")
    confidence_score: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")


class CurrentConfiguration(BaseModel):
    gpu_type: str = Field(..., description="Current GPU type")
    avg_utilization: float = Field(..., description="Average GPU utilization percentage")
    monthly_cost_usd: float = Field(..., description="Current monthly cost in USD")


class CostOptimizationResponse(BaseModel):
    success: bool = Field(..., description="Whether the request was successful")
    current_configuration: Optional[Dict[str, Any]] = Field(default=None, description="Current instance configuration")
    recommendations: List[Dict[str, Any]] = Field(default=[], description="List of cost optimization recommendations")
    estimated_monthly_savings: float = Field(default=0.0, description="Total estimated monthly savings in USD")
    current_gpu: str = Field(..., description="Current GPU type")
    recommended_gpu: str = Field(..., description="Recommended GPU type (same as current if optimal)")
    analysis_period_days: int = Field(..., description="Number of days analyzed")
    data_completeness: float = Field(default=0.0, ge=0, le=1, description="Ratio of expected vs actual data points")
    has_sufficient_data: Optional[bool] = Field(default=True, description="Whether there is sufficient data for analysis")
    warning: Optional[str] = Field(default=None, description="Warning message if any issues")
    message: Optional[str] = Field(default=None, description="Additional message (e.g., 'Already optimized')")


@router.post("/cost-optimization", response_model=CostOptimizationResponse)
async def get_cost_optimization(request: CostOptimizationRequest):
    """
    Get cost optimization recommendations based on historical usage analysis.

    Analyzes the specified number of days of GPU usage data to provide:
    - GPU-to-workload matching recommendations (upgrade/downgrade suggestions)
    - Hibernation timeout optimization based on idle patterns
    - Spot instance timing recommendations for cost savings
    - Estimated monthly savings for each recommendation

    Requirements:
    - Minimum 3 days of historical data required
    - Optimal analysis with 30 days of data
    - Returns confidence scores based on data completeness
    """
    result = await ai_wizard_service.get_cost_optimization_recommendations(
        user_id=request.user_id,
        instance_id=request.instance_id,
        days_to_analyze=request.days_to_analyze,
        current_hibernation_timeout=request.current_hibernation_timeout
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to get cost optimization recommendations")
        )

    return CostOptimizationResponse(
        success=result.get("success", True),
        current_configuration=result.get("current_configuration"),
        recommendations=result.get("recommendations", []),
        estimated_monthly_savings=result.get("estimated_monthly_savings", 0.0),
        current_gpu=result.get("current_gpu", "Unknown"),
        recommended_gpu=result.get("recommended_gpu", "Unknown"),
        analysis_period_days=result.get("analysis_period_days", request.days_to_analyze),
        data_completeness=result.get("data_completeness", 0.0),
        has_sufficient_data=result.get("has_sufficient_data", True),
        warning=result.get("warning"),
        message=result.get("message")
    )


@router.post("/analyze")
async def analyze_project(request: AnalyzeRequest):
    """
    Analyze a project description and return GPU recommendations.

    The AI will either:
    1. Return GPU recommendations if it has enough information
    2. Ask clarifying questions if more details are needed
    """
    # Convert conversation history to dict format
    history = None
    if request.conversation_history:
        history = [{"role": m.role, "content": m.content} for m in request.conversation_history]

    result = await ai_wizard_service.analyze_project(
        project_description=request.project_description,
        conversation_history=history
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail="Failed to analyze project")

    data = result.get("data", {})

    # Retornar no novo formato com campo data completo
    return {
        "success": True,
        "data": data,  # Incluir campo data completo com stage, questions, etc.
        "model_used": result.get("model_used", "unknown"),
        "attempts": result.get("attempts", 1)
    }
