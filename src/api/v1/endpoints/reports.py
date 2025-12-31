"""
Endpoints para Relatórios de Economia Compartilháveis.
"""

import secrets
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.api.v1.dependencies import get_current_user_email
from src.services.savings_calculator import SavingsCalculator
from src.models.shareable_report import ShareableReport
from src.api.v1.schemas.reports import (
    GenerateReportRequest,
    GenerateReportResponse,
    ReportDataResponse,
)

router = APIRouter()


def generate_shareable_id(length: int = 10) -> str:
    """
    Gera um ID único, URL-safe para relatórios compartilháveis.
    Usa secrets.token_urlsafe para gerar IDs seguros e não-sequenciais.
    """
    # token_urlsafe retorna ~1.3x o número de bytes, então ajustamos
    return secrets.token_urlsafe(length)[:length]


@router.post("/generate", response_model=GenerateReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_report(
    request: GenerateReportRequest,
    user_id: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """
    Gera um novo relatório de economia compartilhável.

    - Requer autenticação
    - Aceita configuração de formato (twitter/linkedin/generic) e métricas
    - Retorna shareable_id para URL pública e image_url (após processamento)
    """
    # Gerar ID único para o relatório
    shareable_id = generate_shareable_id()

    # Verificar se ID já existe (muito improvável, mas por segurança)
    existing = db.query(ShareableReport).filter(
        ShareableReport.shareable_id == shareable_id
    ).first()
    if existing:
        # Tentar novamente com novo ID
        shareable_id = generate_shareable_id(12)

    # Obter dados de economia atuais do usuário
    calculator = SavingsCalculator(db)
    savings_summary = calculator.calculate_user_savings(user_id, period="year")

    # Preparar configuração de métricas como dict
    config_dict = request.metrics.model_dump()

    # Preparar dados de economia para armazenamento (snapshot)
    savings_data = {
        "total_savings_vs_aws": savings_summary.get("savings_vs_aws", 0),
        "total_savings_vs_gcp": savings_summary.get("savings_vs_gcp", 0),
        "total_savings_vs_azure": savings_summary.get("savings_vs_azure", 0),
        "savings_percentage_avg": savings_summary.get("savings_percentage_avg", 0),
        "total_hours": savings_summary.get("total_hours", 0),
        "period": "year",
    }

    # Criar registro no banco de dados
    report = ShareableReport(
        user_id=user_id,
        shareable_id=shareable_id,
        config=config_dict,
        format=request.format.value,
        savings_data=savings_data,
        created_at=datetime.utcnow(),
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    return GenerateReportResponse(
        shareable_id=report.shareable_id,
        image_url=report.image_url,  # Será None inicialmente, preenchido após geração da imagem
        format=report.format,
        config=report.config,
        created_at=report.created_at,
    )


@router.get("/{shareable_id}", response_model=ReportDataResponse)
async def get_report(
    shareable_id: str,
    db: Session = Depends(get_db)
):
    """
    Recupera dados públicos de um relatório compartilhável.

    - Endpoint público (não requer autenticação)
    - Retorna apenas dados agregados de economia (sem informações sensíveis)
    """
    report = db.query(ShareableReport).filter(
        ShareableReport.shareable_id == shareable_id
    ).first()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )

    # Retornar apenas dados públicos (privacy filtering)
    return ReportDataResponse(
        shareable_id=report.shareable_id,
        format=report.format,
        savings_data=report.savings_data,
        created_at=report.created_at,
    )
