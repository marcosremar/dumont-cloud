"""
Modelos expandidos para métricas de mercado VAST.ai.

Inclui:
- MarketSnapshot: Snapshots agregados por GPU + tipo de máquina
- ProviderReliability: Histórico de confiabilidade por host
- PricePrediction: Previsões de preço geradas por ML
- CostEfficiencyRanking: Rankings de custo-benefício
- CostForecast: Previsões de custo para 7 dias
- PredictionAccuracy: Rastreamento de precisão das previsões
- BudgetAlert: Alertas de orçamento configuráveis por usuário
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from src.config.database import Base


class MarketSnapshot(Base):
    """
    Snapshot completo do mercado num momento.
    Armazena dados agregados por GPU + tipo de máquina.
    """
    __tablename__ = "market_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Identificação
    gpu_name = Column(String(100), nullable=False, index=True)
    machine_type = Column(String(20), nullable=False, index=True)  # on-demand, interruptible, bid

    # Estatísticas de preço
    min_price = Column(Float, nullable=False)
    max_price = Column(Float, nullable=False)
    avg_price = Column(Float, nullable=False)
    median_price = Column(Float, nullable=False)
    percentile_25 = Column(Float)  # P25
    percentile_75 = Column(Float)  # P75

    # Disponibilidade
    total_offers = Column(Integer, nullable=False)
    available_gpus = Column(Integer, nullable=False)
    verified_offers = Column(Integer, default=0)

    # Performance média
    avg_reliability = Column(Float)
    avg_total_flops = Column(Float)  # TFLOPS médio
    avg_dlperf = Column(Float)       # Deep Learning perf médio
    avg_gpu_mem_bw = Column(Float)   # Memory bandwidth médio (GB/s)

    # Custo-benefício
    min_cost_per_tflops = Column(Float)  # $/TFLOPS mínimo
    avg_cost_per_tflops = Column(Float)  # $/TFLOPS médio
    min_cost_per_gb_vram = Column(Float) # $/GB VRAM mínimo

    # Distribuição geográfica (JSON)
    region_distribution = Column(JSONB)  # {"US": 30, "EU": 45, "ASIA": 10, "OTHER": 15}

    # Índices compostos para queries eficientes
    __table_args__ = (
        Index('idx_market_gpu_type_time', 'gpu_name', 'machine_type', 'timestamp'),
        Index('idx_market_type_time', 'machine_type', 'timestamp'),
    )

    def __repr__(self):
        return f"<MarketSnapshot {self.gpu_name}:{self.machine_type} @ {self.timestamp}>"


class ProviderReliability(Base):
    """
    Histórico de confiabilidade por provedor/host.
    Permite ranking de provedores mais confiáveis.
    """
    __tablename__ = "provider_reliability"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(Integer, nullable=False, unique=True, index=True)  # ID único do host VAST.ai

    # Identificação do host
    hostname = Column(String(200))
    geolocation = Column(String(100))
    verified = Column(Boolean, default=False)
    gpu_name = Column(String(100))  # Tipo principal de GPU do host

    # Scores de confiabilidade (calculados ao longo do tempo)
    reliability_score = Column(Float, default=0.0)  # Score combinado 0-1
    availability_score = Column(Float, default=0.0)  # % tempo disponível
    price_stability_score = Column(Float, default=0.0)  # Estabilidade de preço (menor variação = melhor)
    performance_score = Column(Float, default=0.0)  # Score de performance (TFLOPS, DLPerf)

    # Contadores de observações
    total_observations = Column(Integer, default=0)
    times_available = Column(Integer, default=0)
    times_unavailable = Column(Integer, default=0)

    # Histórico de preços
    min_price_seen = Column(Float)
    max_price_seen = Column(Float)
    avg_price = Column(Float)

    # Performance do host
    avg_dlperf = Column(Float)
    avg_total_flops = Column(Float)

    # Timestamps
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_provider_reliability', 'reliability_score', 'verified'),
        Index('idx_provider_location', 'geolocation'),
        Index('idx_provider_gpu', 'gpu_name'),
    )

    def __repr__(self):
        return f"<ProviderReliability {self.machine_id} score={self.reliability_score:.2f}>"


class PricePrediction(Base):
    """
    Previsões de preço geradas por ML.
    Armazena previsões por hora e dia da semana.
    """
    __tablename__ = "price_predictions"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Alvo da previsão
    gpu_name = Column(String(100), nullable=False, index=True)
    machine_type = Column(String(20), nullable=False, default="on-demand")

    # Previsões por hora (próximas 24h)
    predictions_hourly = Column(JSONB)  # {"0": 0.45, "1": 0.42, ..., "23": 0.48}

    # Previsões por dia da semana
    predictions_daily = Column(JSONB)  # {"monday": 0.44, "tuesday": 0.43, ...}

    # Confiança do modelo
    model_confidence = Column(Float)  # 0-1
    model_version = Column(String(50))

    # Melhor momento previsto
    best_hour_utc = Column(Integer)      # 0-23
    best_day_of_week = Column(Integer)   # 0-6 (Mon-Sun)
    predicted_min_price = Column(Float)

    # Validade da previsão
    valid_until = Column(DateTime)

    __table_args__ = (
        Index('idx_prediction_gpu_type', 'gpu_name', 'machine_type'),
        Index('idx_prediction_validity', 'valid_until'),
    )

    def __repr__(self):
        return f"<PricePrediction {self.gpu_name} valid_until={self.valid_until}>"


class CostEfficiencyRanking(Base):
    """
    Ranking de custo-benefício atualizado periodicamente.
    Cada registro representa uma oferta com seu score de eficiência.
    """
    __tablename__ = "cost_efficiency_rankings"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Identificação
    offer_id = Column(Integer, nullable=False)
    gpu_name = Column(String(100), nullable=False, index=True)
    machine_type = Column(String(20), nullable=False)

    # Preço
    dph_total = Column(Float, nullable=False)  # $/hora

    # Performance
    total_flops = Column(Float)    # TFLOPS
    gpu_ram = Column(Float)        # GB
    dlperf = Column(Float)         # DL performance score
    gpu_mem_bw = Column(Float)     # Memory bandwidth (GB/s)

    # Scores de custo-benefício
    cost_per_tflops = Column(Float)    # $/TFLOPS
    cost_per_gb_vram = Column(Float)   # $/GB VRAM
    cost_per_dlperf = Column(Float)    # $/DLPerf

    # Score composto (normalizado 0-100)
    efficiency_score = Column(Float, nullable=False)

    # Ranking
    rank_overall = Column(Integer)
    rank_in_gpu_class = Column(Integer)

    # Metadados do host
    reliability = Column(Float)
    verified = Column(Boolean)
    geolocation = Column(String(100))
    machine_id = Column(Integer)  # Para correlacionar com provider_reliability

    __table_args__ = (
        Index('idx_efficiency_score', 'efficiency_score'),
        Index('idx_efficiency_gpu', 'gpu_name', 'efficiency_score'),
        Index('idx_efficiency_timestamp', 'timestamp'),
    )

    def __repr__(self):
        return f"<CostEfficiencyRanking {self.gpu_name} rank={self.rank_overall} score={self.efficiency_score:.1f}>"


class CostForecast(Base):
    """
    Previsões de custo para os próximos 7 dias.
    Armazena previsões horárias (168 horas) e custos diários agregados.
    """
    __tablename__ = "cost_forecasts"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Identificação do usuário (para forecasts personalizados)
    user_id = Column(Integer, nullable=True, index=True)

    # Alvo da previsão
    gpu_name = Column(String(100), nullable=False, index=True)
    machine_type = Column(String(20), nullable=False, default="on-demand")

    # Período da previsão
    forecast_start = Column(DateTime, nullable=False)
    forecast_end = Column(DateTime, nullable=False)

    # Previsões horárias (168 horas = 7 dias)
    # {"0": 0.45, "1": 0.42, ..., "167": 0.48}
    hourly_prices = Column(JSONB, nullable=False)

    # Custos diários agregados
    # [{"date": "2024-01-01", "cost": 10.50, "hours": 24}, ...]
    daily_costs = Column(JSONB, nullable=False)

    # Intervalos de confiança por dia
    # [{"date": "2024-01-01", "lower": 9.50, "upper": 11.50}, ...]
    confidence_intervals = Column(JSONB)

    # Custo total previsto para os 7 dias
    total_forecasted_cost = Column(Float, nullable=False)

    # Metadados do modelo
    model_version = Column(String(50))
    model_confidence = Column(Float)  # 0-1

    # Padrões de uso do usuário considerados
    # {"avg_hours_per_day": 8, "typical_start_hour": 9, "typical_end_hour": 17}
    usage_pattern = Column(JSONB)

    # Melhor janela de custo prevista
    best_window_start = Column(DateTime)
    best_window_end = Column(DateTime)
    best_window_cost = Column(Float)

    # Validade da previsão
    valid_until = Column(DateTime, nullable=False)

    __table_args__ = (
        Index('idx_forecast_user', 'user_id'),
        Index('idx_forecast_gpu_type', 'gpu_name', 'machine_type'),
        Index('idx_forecast_validity', 'valid_until'),
        Index('idx_forecast_period', 'forecast_start', 'forecast_end'),
    )

    def __repr__(self):
        return f"<CostForecast {self.gpu_name} ${self.total_forecasted_cost:.2f} valid_until={self.valid_until}>"


class PredictionAccuracy(Base):
    """
    Rastreamento de precisão das previsões de preço.
    Armazena métricas de acurácia comparando previsões com valores reais.
    """
    __tablename__ = "prediction_accuracy"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Identificação
    gpu_name = Column(String(100), nullable=False, index=True)
    machine_type = Column(String(20), nullable=False, default="on-demand")

    # Período de avaliação
    evaluation_start = Column(DateTime, nullable=False)
    evaluation_end = Column(DateTime, nullable=False)

    # Métricas de acurácia
    mape = Column(Float, nullable=False)  # Mean Absolute Percentage Error (0-100%)
    mae = Column(Float)  # Mean Absolute Error (em $/hora)
    rmse = Column(Float)  # Root Mean Square Error
    r_squared = Column(Float)  # Coeficiente de determinação R²

    # Contagem de amostras
    num_predictions = Column(Integer, nullable=False)
    num_actual_values = Column(Integer, nullable=False)

    # Metadados do modelo avaliado
    model_version = Column(String(50))

    # Detalhes por hora (opcional)
    # {"0": {"mape": 5.2, "mae": 0.02}, "1": {"mape": 4.8, "mae": 0.018}, ...}
    hourly_accuracy = Column(JSONB)

    # Detalhes por dia (opcional)
    # {"monday": {"mape": 5.5, "mae": 0.022}, "tuesday": {"mape": 4.9, "mae": 0.019}, ...}
    daily_accuracy = Column(JSONB)

    __table_args__ = (
        Index('idx_accuracy_gpu_type', 'gpu_name', 'machine_type'),
        Index('idx_accuracy_created', 'created_at'),
        Index('idx_accuracy_mape', 'mape'),
    )

    def __repr__(self):
        return f"<PredictionAccuracy {self.gpu_name}:{self.machine_type} MAPE={self.mape:.2f}%>"


class BudgetAlert(Base):
    """
    Configuração de alertas de orçamento por usuário.
    Dispara notificação quando custo previsto excede o limiar configurado.
    """
    __tablename__ = "budget_alerts"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Identificação do usuário
    user_id = Column(Integer, nullable=False, index=True)

    # Configuração do alerta
    gpu_name = Column(String(100), nullable=True, index=True)  # Null = todos os GPUs
    machine_type = Column(String(20), nullable=False, default="on-demand")
    threshold_amount = Column(Float, nullable=False)  # Limiar em $ para 7 dias

    # Contato para notificação
    email = Column(String(255), nullable=False)

    # Estado do alerta
    enabled = Column(Boolean, default=True, nullable=False)

    # Histórico de disparo
    last_triggered_at = Column(DateTime, nullable=True)
    last_forecasted_cost = Column(Float, nullable=True)  # Último custo previsto que disparou alerta

    # Metadados
    alert_name = Column(String(100), nullable=True)  # Nome amigável (opcional)
    notification_settings = Column(JSONB, nullable=True)  # Configurações extras (cooldown, frequência, etc)

    __table_args__ = (
        Index('idx_budget_alert_user', 'user_id'),
        Index('idx_budget_alert_enabled', 'enabled'),
        Index('idx_budget_alert_user_gpu', 'user_id', 'gpu_name'),
    )

    def __repr__(self):
        gpu = self.gpu_name or "ALL"
        return f"<BudgetAlert user={self.user_id} gpu={gpu} threshold=${self.threshold_amount:.2f}>"
