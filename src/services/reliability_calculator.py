"""
Reliability Score Calculation Service

Calcula scores de confiabilidade para máquinas GPU baseado em:
- Percentual de uptime
- Taxa de interrupções
- Avaliações de usuários

O score final é uma combinação ponderada desses fatores,
normalizado para uma escala de 0-100.
"""
from typing import Optional


# Pesos padrão para cálculo de confiabilidade
DEFAULT_WEIGHTS = {
    "uptime": 0.4,           # 40% do peso
    "interruption": 0.4,     # 40% do peso
    "user_rating": 0.2,      # 20% do peso
}

# Pesos quando não há ratings (redistribuído)
NO_RATING_WEIGHTS = {
    "uptime": 0.5,           # 50% do peso
    "interruption": 0.5,     # 50% do peso
}


def calculate_reliability_score(
    uptime_pct: float,
    interruption_rate: float,
    avg_rating: Optional[float] = None,
    rating_count: int = 0,
    weights: Optional[dict] = None,
) -> float:
    """
    Calcula score de confiabilidade ponderado para uma máquina.

    O score é calculado usando uma combinação ponderada de:
    - Uptime percentage: Contribui positivamente (maior = melhor)
    - Interruption rate: Contribui negativamente (menor = melhor)
    - User ratings: Contribui positivamente (maior = melhor)

    Quando não há ratings disponíveis, os pesos são redistribuídos
    para 50/50 entre uptime e interruption rate.

    Args:
        uptime_pct: Percentual de uptime (0.0 a 1.0 ou 0 a 100).
                   Valores > 1 são tratados como percentual (0-100).
        interruption_rate: Taxa de interrupções (0.0 a 1.0).
                          0 = sem interrupções (melhor)
                          1 = sempre interrompido (pior)
        avg_rating: Média de ratings de usuários (1.0 a 5.0).
                   None se não houver ratings.
        rating_count: Número de ratings disponíveis.
                     Se 0, os pesos são redistribuídos.
        weights: Dicionário opcional com pesos customizados.
                Keys: 'uptime', 'interruption', 'user_rating'

    Returns:
        float: Score de confiabilidade de 0 a 100.
              Valores mais altos indicam maior confiabilidade.

    Examples:
        >>> calculate_reliability_score(0.95, 0.02, 4.5, 10)
        91.5  # Máquina excelente

        >>> calculate_reliability_score(0.8, 0.1, None, 0)
        85.0  # Boa máquina sem ratings (50/50 uptime/interruption)

        >>> calculate_reliability_score(0.5, 0.3, 2.0, 5)
        47.0  # Máquina problemática
    """
    # Normalizar uptime_pct para 0-100
    # Suporta entrada como 0-1 ou 0-100
    if uptime_pct <= 1.0:
        uptime_score = uptime_pct * 100
    else:
        uptime_score = uptime_pct

    # Garantir que está no range válido
    uptime_score = min(100.0, max(0.0, uptime_score))

    # Calcular score de interrupção (inverso: menos interrupções = melhor)
    # interruption_rate 0 = 100 pontos, 1 = 0 pontos
    clamped_interruption = min(1.0, max(0.0, interruption_rate))
    interruption_score = (1.0 - clamped_interruption) * 100

    # Determinar se há ratings válidos
    has_ratings = rating_count > 0 and avg_rating is not None

    # Usar pesos customizados ou padrão
    if weights is not None:
        w = weights
    elif has_ratings:
        w = DEFAULT_WEIGHTS
    else:
        w = NO_RATING_WEIGHTS

    # Se não há ratings, usar apenas uptime e interruption (50/50)
    if not has_ratings:
        weighted_score = (
            (uptime_score * w.get("uptime", 0.5)) +
            (interruption_score * w.get("interruption", 0.5))
        )
        return round(weighted_score, 1)

    # Normalizar rating de 1-5 para 0-100
    # Rating 1 = 0 pontos, Rating 5 = 100 pontos
    clamped_rating = min(5.0, max(1.0, avg_rating))
    rating_score = ((clamped_rating - 1.0) / 4.0) * 100

    # Calcular score ponderado
    weighted_score = (
        (uptime_score * w.get("uptime", 0.4)) +
        (interruption_score * w.get("interruption", 0.4)) +
        (rating_score * w.get("user_rating", 0.2))
    )

    return round(weighted_score, 1)


def get_recommendation(score: float) -> str:
    """
    Retorna recomendação textual baseada no score de confiabilidade.

    Args:
        score: Score de confiabilidade (0-100)

    Returns:
        str: Categoria da recomendação:
            - 'excellent': Score >= 90
            - 'good': Score >= 75
            - 'fair': Score >= 60
            - 'poor': Score < 60
    """
    if score >= 90:
        return "excellent"
    elif score >= 75:
        return "good"
    elif score >= 60:
        return "fair"
    return "poor"


def calculate_weighted_average(
    scores: list[tuple[float, float]],
    min_weight: float = 0.0,
) -> Optional[float]:
    """
    Calcula média ponderada de múltiplos scores.

    Útil para agregar scores de múltiplas fontes ou períodos.

    Args:
        scores: Lista de tuplas (score, weight).
        min_weight: Peso mínimo total necessário para retornar resultado.

    Returns:
        float: Média ponderada ou None se peso total < min_weight.

    Example:
        >>> scores = [(95.0, 10), (85.0, 5), (90.0, 3)]
        >>> calculate_weighted_average(scores)
        91.4  # (95*10 + 85*5 + 90*3) / (10+5+3)
    """
    if not scores:
        return None

    total_weight = sum(weight for _, weight in scores)
    if total_weight < min_weight:
        return None

    weighted_sum = sum(score * weight for score, weight in scores)
    return round(weighted_sum / total_weight, 1)


def normalize_uptime(
    uptime_seconds: float,
    total_seconds: float,
) -> float:
    """
    Converte uptime em segundos para percentual.

    Args:
        uptime_seconds: Tempo de uptime em segundos.
        total_seconds: Tempo total do período em segundos.

    Returns:
        float: Percentual de uptime (0.0 a 1.0)
    """
    if total_seconds <= 0:
        return 0.0
    return min(1.0, max(0.0, uptime_seconds / total_seconds))


def calculate_interruption_rate(
    interruption_count: int,
    days: int,
    max_interruptions_per_day: float = 10.0,
) -> float:
    """
    Calcula taxa de interrupção normalizada.

    Args:
        interruption_count: Número total de interrupções no período.
        days: Número de dias no período.
        max_interruptions_per_day: Número máximo esperado de interrupções
                                   por dia (para normalização).

    Returns:
        float: Taxa de interrupção normalizada (0.0 a 1.0).
              0.0 = sem interrupções
              1.0 = muitas interrupções (atingiu ou excedeu max)
    """
    if days <= 0:
        return 0.0

    interruptions_per_day = interruption_count / days
    normalized = interruptions_per_day / max_interruptions_per_day
    return min(1.0, max(0.0, normalized))
