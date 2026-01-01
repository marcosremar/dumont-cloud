"""
Budget Alert Service - Sistema de alertas de orçamento para Dumont Cloud

Monitora previsões de custo e envia notificações por email quando
valores ultrapassam thresholds configurados pelo usuário.
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
import time

logger = logging.getLogger(__name__)


@dataclass
class BudgetAlertData:
    """Representa dados de um alerta de orçamento"""
    alert_id: str
    user_id: str
    email: str
    gpu_name: str
    threshold_amount: float
    forecasted_cost: float
    time_range_days: int
    confidence_interval: List[float]
    optimal_windows: Optional[List[Dict]] = None
    recommendations: Optional[List[str]] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        """Converte para dict"""
        return {
            'alert_id': self.alert_id,
            'user_id': self.user_id,
            'email': self.email,
            'gpu_name': self.gpu_name,
            'threshold_amount': self.threshold_amount,
            'forecasted_cost': self.forecasted_cost,
            'time_range_days': self.time_range_days,
            'confidence_interval': self.confidence_interval,
            'optimal_windows': self.optimal_windows,
            'recommendations': self.recommendations,
            'timestamp': self.timestamp,
            'timestamp_iso': datetime.fromtimestamp(self.timestamp).isoformat(),
            'exceeded_by': round(self.forecasted_cost - self.threshold_amount, 2),
            'exceeded_percent': round(
                ((self.forecasted_cost - self.threshold_amount) / self.threshold_amount) * 100, 1
            ) if self.threshold_amount > 0 else 0,
        }


@dataclass
class SMTPConfig:
    """Configuração SMTP para envio de emails"""
    host: str
    port: int
    user: str
    password: str
    from_email: str
    use_tls: bool = True


class BudgetAlertService:
    """
    Serviço de alertas de orçamento.

    Compara previsões de custo com thresholds do usuário e envia
    notificações por email quando o orçamento é excedido.

    Funcionalidades:
    - Envio de emails via SMTP (Gmail, etc.)
    - Templates de email com previsões e recomendações
    - Histórico de alertas enviados
    - Cooldown para evitar spam
    """

    DEFAULT_COOLDOWN_SECONDS = 3600  # 1 hora entre alertas iguais

    def __init__(self, smtp_config: Optional[SMTPConfig] = None):
        """
        Inicializa o serviço de alertas.

        Args:
            smtp_config: Configuração SMTP. Se não fornecido,
                        usa variáveis de ambiente.
        """
        self.smtp_config = smtp_config or self._load_smtp_config_from_env()
        self.alert_history: List[BudgetAlertData] = []
        self.last_alert_time: Dict[str, float] = {}

        if self.smtp_config:
            logger.info("BudgetAlertService initialized with SMTP config")
        else:
            logger.warning("BudgetAlertService initialized without SMTP config - email sending disabled")

    def _load_smtp_config_from_env(self) -> Optional[SMTPConfig]:
        """Carrega configuração SMTP de variáveis de ambiente."""
        host = os.getenv('SMTP_HOST')
        port = os.getenv('SMTP_PORT')
        user = os.getenv('SMTP_USER')
        password = os.getenv('SMTP_PASSWORD')
        from_email = os.getenv('ALERT_EMAIL_FROM')

        if not all([host, port, user, password, from_email]):
            logger.warning(
                "SMTP configuration incomplete. Required env vars: "
                "SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, ALERT_EMAIL_FROM"
            )
            return None

        return SMTPConfig(
            host=host,
            port=int(port),
            user=user,
            password=password,
            from_email=from_email,
            use_tls=True,
        )

    def check_budget_threshold(
        self,
        user_id: str,
        email: str,
        gpu_name: str,
        threshold_amount: float,
        forecasted_cost: float,
        time_range_days: int = 7,
        confidence_interval: Optional[List[float]] = None,
        optimal_windows: Optional[List[Dict]] = None,
    ) -> Optional[BudgetAlertData]:
        """
        Verifica se previsão de custo excede threshold e prepara alerta.

        Args:
            user_id: ID do usuário
            email: Email do usuário
            gpu_name: Nome da GPU
            threshold_amount: Limite de orçamento configurado
            forecasted_cost: Custo previsto
            time_range_days: Período da previsão em dias
            confidence_interval: [lower, upper] bounds
            optimal_windows: Janelas de tempo recomendadas

        Returns:
            BudgetAlertData se threshold foi excedido, None caso contrário
        """
        if forecasted_cost <= threshold_amount:
            logger.debug(
                f"Budget OK for {user_id}: ${forecasted_cost:.2f} <= ${threshold_amount:.2f}"
            )
            return None

        # Gerar recomendações
        recommendations = self._generate_recommendations(
            forecasted_cost=forecasted_cost,
            threshold_amount=threshold_amount,
            gpu_name=gpu_name,
            optimal_windows=optimal_windows,
        )

        alert = BudgetAlertData(
            alert_id=f"budget_{user_id}_{gpu_name}_{int(time.time())}",
            user_id=user_id,
            email=email,
            gpu_name=gpu_name,
            threshold_amount=threshold_amount,
            forecasted_cost=forecasted_cost,
            time_range_days=time_range_days,
            confidence_interval=confidence_interval or [
                forecasted_cost * 0.9,
                forecasted_cost * 1.1,
            ],
            optimal_windows=optimal_windows,
            recommendations=recommendations,
        )

        logger.warning(
            f"Budget threshold exceeded for {user_id}/{gpu_name}: "
            f"${forecasted_cost:.2f} > ${threshold_amount:.2f}"
        )

        return alert

    def _generate_recommendations(
        self,
        forecasted_cost: float,
        threshold_amount: float,
        gpu_name: str,
        optimal_windows: Optional[List[Dict]] = None,
    ) -> List[str]:
        """Gera recomendações para reduzir custos."""
        recommendations = []

        exceeded_by = forecasted_cost - threshold_amount
        exceeded_percent = (exceeded_by / threshold_amount) * 100 if threshold_amount > 0 else 0

        # Recomendação baseada na magnitude do excesso
        if exceeded_percent > 50:
            recommendations.append(
                f"Consider reducing GPU usage hours or switching to a more cost-effective GPU model."
            )
        elif exceeded_percent > 20:
            recommendations.append(
                f"Scheduling workloads during off-peak hours could save up to 30%."
            )
        else:
            recommendations.append(
                f"Minor adjustments to your schedule could bring costs within budget."
            )

        # Recomendação de janelas ótimas
        if optimal_windows and len(optimal_windows) > 0:
            best_window = optimal_windows[0]
            savings = best_window.get('savings_amount', 0)
            if savings > 0:
                recommendations.append(
                    f"Running jobs at optimal times could save approximately ${savings:.2f}."
                )

        # Recomendação de GPU alternativa
        recommendations.append(
            f"Check if a different GPU model could meet your needs at a lower cost."
        )

        # Recomendação de tipo de máquina
        recommendations.append(
            f"Using interruptible (spot) instances can reduce costs by 50-80% compared to on-demand."
        )

        return recommendations

    def send_alert(
        self,
        alert: BudgetAlertData,
        force: bool = False,
    ) -> bool:
        """
        Envia alerta de orçamento por email.

        Args:
            alert: Dados do alerta
            force: Ignorar cooldown e enviar mesmo assim

        Returns:
            True se email foi enviado com sucesso
        """
        if not self.smtp_config:
            logger.error("Cannot send alert: SMTP not configured")
            return False

        # Verificar cooldown
        alert_key = f"{alert.user_id}_{alert.gpu_name}"
        last_time = self.last_alert_time.get(alert_key, 0)

        if not force and (time.time() - last_time) < self.DEFAULT_COOLDOWN_SECONDS:
            logger.info(
                f"Alert for {alert_key} in cooldown period, skipping email"
            )
            return False

        try:
            # Criar mensagem
            msg = self._create_email_message(alert)

            # Enviar via SMTP
            self._send_smtp_email(msg, alert.email)

            # Atualizar histórico e cooldown
            self.alert_history.append(alert)
            self.last_alert_time[alert_key] = time.time()

            logger.info(f"Budget alert sent to {alert.email} for {alert.gpu_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to send budget alert to {alert.email}: {e}")
            return False

    def _create_email_message(self, alert: BudgetAlertData) -> MIMEMultipart:
        """Cria mensagem de email formatada."""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Budget Alert: {alert.gpu_name} forecast exceeds threshold"
        msg['From'] = self.smtp_config.from_email
        msg['To'] = alert.email

        # Versão texto
        text_content = self._create_text_content(alert)
        msg.attach(MIMEText(text_content, 'plain'))

        # Versão HTML
        html_content = self._create_html_content(alert)
        msg.attach(MIMEText(html_content, 'html'))

        return msg

    def _create_text_content(self, alert: BudgetAlertData) -> str:
        """Cria conteúdo texto do email."""
        alert_dict = alert.to_dict()

        lines = [
            "BUDGET ALERT - Dumont Cloud",
            "",
            f"GPU: {alert.gpu_name}",
            f"Time Period: Next {alert.time_range_days} days",
            "",
            "COST FORECAST:",
            f"  Forecasted Cost: ${alert.forecasted_cost:.2f}",
            f"  Your Threshold:  ${alert.threshold_amount:.2f}",
            f"  Exceeded By:     ${alert_dict['exceeded_by']:.2f} ({alert_dict['exceeded_percent']:.1f}%)",
            "",
            f"Confidence Interval: ${alert.confidence_interval[0]:.2f} - ${alert.confidence_interval[1]:.2f}",
            "",
            "RECOMMENDATIONS:",
        ]

        if alert.recommendations:
            for i, rec in enumerate(alert.recommendations, 1):
                lines.append(f"  {i}. {rec}")

        if alert.optimal_windows:
            lines.append("")
            lines.append("OPTIMAL TIME WINDOWS:")
            for window in alert.optimal_windows[:3]:
                start = window.get('start_time', 'N/A')
                end = window.get('end_time', 'N/A')
                cost = window.get('estimated_cost', 0)
                lines.append(f"  - {start} to {end}: ${cost:.2f}")

        lines.extend([
            "",
            "---",
            "Manage your budget alerts at: https://dumontcloud.com/settings/budget",
            "Dumont Cloud - GPU Cloud Computing",
        ])

        return "\n".join(lines)

    def _create_html_content(self, alert: BudgetAlertData) -> str:
        """Cria conteúdo HTML do email."""
        alert_dict = alert.to_dict()

        recommendations_html = ""
        if alert.recommendations:
            recommendations_html = "<ul>" + "".join(
                f"<li>{rec}</li>" for rec in alert.recommendations
            ) + "</ul>"

        optimal_windows_html = ""
        if alert.optimal_windows:
            rows = ""
            for window in alert.optimal_windows[:3]:
                start = window.get('start_time', 'N/A')
                end = window.get('end_time', 'N/A')
                cost = window.get('estimated_cost', 0)
                savings = window.get('savings_amount', 0)
                rows += f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">{start}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{end}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">${cost:.2f}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; color: #22c55e;">-${savings:.2f}</td>
                </tr>
                """
            optimal_windows_html = f"""
            <h3>Optimal Time Windows</h3>
            <table style="border-collapse: collapse; width: 100%;">
                <thead>
                    <tr style="background-color: #1e293b; color: white;">
                        <th style="padding: 8px; border: 1px solid #ddd;">Start</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">End</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">Cost</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">Savings</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                       background-color: #0f172a; color: #e2e8f0; margin: 0; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: #1e293b;
                             border-radius: 8px; padding: 20px; }}
                .header {{ text-align: center; padding-bottom: 20px; border-bottom: 1px solid #334155; }}
                .alert-badge {{ display: inline-block; background-color: #ef4444; color: white;
                               padding: 4px 12px; border-radius: 4px; font-size: 12px;
                               text-transform: uppercase; font-weight: bold; }}
                .cost-card {{ background-color: #334155; border-radius: 8px; padding: 16px;
                             margin: 16px 0; }}
                .cost-row {{ display: flex; justify-content: space-between; padding: 8px 0; }}
                .cost-label {{ color: #94a3b8; }}
                .cost-value {{ font-weight: bold; }}
                .exceeded {{ color: #ef4444; }}
                .footer {{ text-align: center; padding-top: 20px; border-top: 1px solid #334155;
                          font-size: 12px; color: #64748b; margin-top: 20px; }}
                h2 {{ color: #f8fafc; margin-top: 24px; }}
                h3 {{ color: #f8fafc; }}
                a {{ color: #3b82f6; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <span class="alert-badge">Budget Alert</span>
                    <h1 style="margin: 16px 0 8px 0;">Dumont Cloud</h1>
                    <p style="color: #94a3b8; margin: 0;">Cost forecast exceeds your budget threshold</p>
                </div>

                <h2>{alert.gpu_name}</h2>
                <p style="color: #94a3b8;">Forecast for the next {alert.time_range_days} days</p>

                <div class="cost-card">
                    <div class="cost-row">
                        <span class="cost-label">Forecasted Cost</span>
                        <span class="cost-value exceeded">${alert.forecasted_cost:.2f}</span>
                    </div>
                    <div class="cost-row">
                        <span class="cost-label">Your Threshold</span>
                        <span class="cost-value">${alert.threshold_amount:.2f}</span>
                    </div>
                    <div class="cost-row" style="border-top: 1px solid #475569; padding-top: 12px;">
                        <span class="cost-label">Exceeded By</span>
                        <span class="cost-value exceeded">
                            ${alert_dict['exceeded_by']:.2f} ({alert_dict['exceeded_percent']:.1f}%)
                        </span>
                    </div>
                    <div class="cost-row">
                        <span class="cost-label">Confidence Range</span>
                        <span class="cost-value">
                            ${alert.confidence_interval[0]:.2f} - ${alert.confidence_interval[1]:.2f}
                        </span>
                    </div>
                </div>

                <h3>Recommendations</h3>
                {recommendations_html}

                {optimal_windows_html}

                <div class="footer">
                    <p>
                        <a href="https://dumontcloud.com/settings/budget">Manage Budget Alerts</a>
                    </p>
                    <p>Dumont Cloud - GPU Cloud Computing</p>
                </div>
            </div>
        </body>
        </html>
        """

        return html

    def _send_smtp_email(self, msg: MIMEMultipart, to_email: str) -> None:
        """Envia email via SMTP."""
        with smtplib.SMTP(self.smtp_config.host, self.smtp_config.port) as server:
            if self.smtp_config.use_tls:
                server.starttls()

            server.login(self.smtp_config.user, self.smtp_config.password)
            server.send_message(msg)

    def send_alert_async(
        self,
        alert: BudgetAlertData,
        force: bool = False,
    ) -> None:
        """
        Envia alerta de forma assíncrona (para uso com FastAPI BackgroundTasks).

        Esta função é projetada para ser usada com FastAPI BackgroundTasks:

        ```python
        from fastapi import BackgroundTasks

        @router.post("/check-budget")
        async def check_budget(background_tasks: BackgroundTasks):
            alert = budget_service.check_budget_threshold(...)
            if alert:
                background_tasks.add_task(
                    budget_service.send_alert_async,
                    alert
                )
            return {"status": "ok"}
        ```

        Args:
            alert: Dados do alerta
            force: Ignorar cooldown
        """
        try:
            success = self.send_alert(alert, force=force)
            if not success:
                logger.warning(f"Background alert send failed for {alert.email}")
        except Exception as e:
            # Log error but don't raise - this is a background task
            logger.error(f"Error in background alert send: {e}")

    def get_alert_history(
        self,
        user_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """
        Retorna histórico de alertas enviados.

        Args:
            user_id: Filtrar por usuário (opcional)
            limit: Número máximo de alertas

        Returns:
            Lista de alertas em formato dict
        """
        alerts = self.alert_history

        if user_id:
            alerts = [a for a in alerts if a.user_id == user_id]

        # Ordenar por timestamp (mais recente primeiro)
        alerts = sorted(alerts, key=lambda a: a.timestamp, reverse=True)

        return [a.to_dict() for a in alerts[:limit]]

    def clear_cooldown(self, user_id: str, gpu_name: str) -> bool:
        """
        Limpa cooldown para permitir envio imediato de alerta.

        Args:
            user_id: ID do usuário
            gpu_name: Nome da GPU

        Returns:
            True se cooldown foi limpo
        """
        alert_key = f"{user_id}_{gpu_name}"
        if alert_key in self.last_alert_time:
            del self.last_alert_time[alert_key]
            logger.info(f"Cooldown cleared for {alert_key}")
            return True
        return False


# Singleton instance
_budget_alert_service: Optional[BudgetAlertService] = None


def get_budget_alert_service(
    smtp_config: Optional[SMTPConfig] = None,
) -> BudgetAlertService:
    """
    Retorna instância singleton do BudgetAlertService.

    Args:
        smtp_config: Configuração SMTP (opcional, usa env vars se não fornecido)
    """
    global _budget_alert_service

    if _budget_alert_service is None:
        _budget_alert_service = BudgetAlertService(smtp_config=smtp_config)

    return _budget_alert_service


# Função helper para uso com FastAPI BackgroundTasks
async def send_budget_alert_background(
    email: str,
    user_id: str,
    gpu_name: str,
    forecast: Dict,
    threshold: float,
) -> None:
    """
    Helper para enviar alerta de orçamento em background.

    Uso com FastAPI:
    ```python
    from fastapi import BackgroundTasks

    @router.post("/check-budget")
    async def check_budget(
        request: BudgetCheckRequest,
        background_tasks: BackgroundTasks
    ):
        background_tasks.add_task(
            send_budget_alert_background,
            email=request.email,
            user_id=request.user_id,
            gpu_name=request.gpu_name,
            forecast=forecast_data,
            threshold=request.threshold,
        )
        return {"status": "checking"}
    ```
    """
    service = get_budget_alert_service()

    # Extrair dados do forecast
    forecasted_cost = forecast.get('total_cost', 0)
    confidence_interval = forecast.get('confidence_interval', [
        forecasted_cost * 0.9,
        forecasted_cost * 1.1,
    ])
    optimal_windows = forecast.get('optimal_windows', [])

    alert = service.check_budget_threshold(
        user_id=user_id,
        email=email,
        gpu_name=gpu_name,
        threshold_amount=threshold,
        forecasted_cost=forecasted_cost,
        time_range_days=forecast.get('days', 7),
        confidence_interval=confidence_interval,
        optimal_windows=optimal_windows,
    )

    if alert:
        service.send_alert(alert)


if __name__ == "__main__":
    # Exemplo de uso
    logging.basicConfig(level=logging.INFO)

    print("\nTesting BudgetAlertService...\n")

    # Criar serviço (sem SMTP para teste)
    service = BudgetAlertService()

    # Testar verificação de threshold
    alert = service.check_budget_threshold(
        user_id="user-123",
        email="test@example.com",
        gpu_name="RTX 4090",
        threshold_amount=100.0,
        forecasted_cost=125.50,
        time_range_days=7,
        optimal_windows=[
            {
                "start_time": "2024-01-15 02:00",
                "end_time": "2024-01-15 10:00",
                "estimated_cost": 95.0,
                "savings_amount": 30.50,
            }
        ],
    )

    if alert:
        print(f"Alert created: {alert.alert_id}")
        print(f"Exceeded by: ${alert.to_dict()['exceeded_by']:.2f}")
        print(f"Recommendations: {len(alert.recommendations)}")

        # Mostrar preview do email (sem enviar)
        print("\n--- Email Preview (text) ---")
        print(service._create_text_content(alert))

    print("\nTest completed!")
