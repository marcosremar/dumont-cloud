"""
Serviço de previsão de preços usando ML.

Usa dados históricos para prever melhores horários/dias para alugar GPUs.
Utiliza Random Forest para capturar padrões sazonais.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import statistics
from collections import defaultdict
import math

from src.config.database import SessionLocal
from src.models.metrics import MarketSnapshot, PricePrediction

logger = logging.getLogger(__name__)


class PricePredictionService:
    """
    Serviço de previsão de preços.

    Usa Random Forest para prever preços baseado em:
    - Hora do dia (0-23)
    - Dia da semana (0-6)
    - Tendência recente
    """

    MODEL_VERSION = "simple_v1.0"

    def __init__(self):
        self.models: Dict[str, any] = {}
        self.scalers: Dict[str, any] = {}
        self.last_trained: Dict[str, datetime] = {}
        self._ml_available = self._check_ml_available()

    def _check_ml_available(self) -> bool:
        """Verifica se sklearn está disponível."""
        try:
            import numpy as np
            from sklearn.ensemble import RandomForestRegressor
            from sklearn.preprocessing import StandardScaler
            return True
        except ImportError:
            logger.warning("scikit-learn não disponível. Usando previsão simples baseada em médias.")
            return False

    def train_model(
        self,
        gpu_name: str,
        machine_type: str = "on-demand",
        days_of_history: int = 30,
    ) -> bool:
        """
        Treina modelo de previsão para uma GPU/tipo.

        Args:
            gpu_name: Nome da GPU
            machine_type: Tipo de máquina
            days_of_history: Dias de histórico para treino

        Returns:
            True se treino foi bem sucedido
        """
        key = f"{gpu_name}:{machine_type}"
        db = SessionLocal()

        try:
            # Buscar histórico
            start_time = datetime.utcnow() - timedelta(days=days_of_history)
            records = db.query(MarketSnapshot).filter(
                MarketSnapshot.gpu_name == gpu_name,
                MarketSnapshot.machine_type == machine_type,
                MarketSnapshot.timestamp >= start_time,
            ).order_by(MarketSnapshot.timestamp).all()

            if len(records) < 50:  # Mínimo de dados
                logger.warning(f"Dados insuficientes para treinar {key}: {len(records)} registros")
                return False

            if self._ml_available:
                return self._train_ml_model(key, records)
            else:
                return self._train_simple_model(key, records)

        except Exception as e:
            logger.error(f"Erro ao treinar modelo para {key}: {e}")
            return False
        finally:
            db.close()

    def _train_ml_model(self, key: str, records: List[MarketSnapshot]) -> bool:
        """Treina modelo usando scikit-learn."""
        try:
            import numpy as np
            from sklearn.ensemble import RandomForestRegressor
            from sklearn.preprocessing import StandardScaler

            # Preparar features
            X = []
            y = []

            for record in records:
                features = self._extract_features(record.timestamp)
                X.append(features)
                y.append(record.avg_price)

            X = np.array(X)
            y = np.array(y)

            # Normalizar features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            # Treinar modelo
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
            )
            model.fit(X_scaled, y)

            # Salvar modelo
            self.models[key] = model
            self.scalers[key] = scaler
            self.last_trained[key] = datetime.utcnow()

            logger.info(f"Modelo ML treinado para {key} com {len(records)} amostras")
            return True

        except Exception as e:
            logger.error(f"Erro ao treinar modelo ML: {e}")
            return False

    def _train_simple_model(self, key: str, records: List[MarketSnapshot]) -> bool:
        """Treina modelo simples baseado em médias por hora/dia."""
        try:
            # Agrupar por hora
            hourly_prices = defaultdict(list)
            daily_prices = defaultdict(list)

            for record in records:
                hour = record.timestamp.hour
                day = record.timestamp.weekday()
                hourly_prices[hour].append(record.avg_price)
                daily_prices[day].append(record.avg_price)

            # Calcular médias
            hourly_avg = {h: statistics.mean(prices) for h, prices in hourly_prices.items()}
            daily_avg = {d: statistics.mean(prices) for d, prices in daily_prices.items()}

            self.models[key] = {
                'hourly': hourly_avg,
                'daily': daily_avg,
                'overall_avg': statistics.mean([r.avg_price for r in records]),
            }
            self.last_trained[key] = datetime.utcnow()

            logger.info(f"Modelo simples treinado para {key} com {len(records)} amostras")
            return True

        except Exception as e:
            logger.error(f"Erro ao treinar modelo simples: {e}")
            return False

    def _extract_features(self, timestamp: datetime) -> List[float]:
        """Extrai features de um timestamp."""
        return [
            timestamp.hour,                                    # 0-23
            timestamp.weekday(),                               # 0-6 (Mon-Sun)
            math.sin(2 * math.pi * timestamp.hour / 24),       # Hora cíclica (sin)
            math.cos(2 * math.pi * timestamp.hour / 24),       # Hora cíclica (cos)
            math.sin(2 * math.pi * timestamp.weekday() / 7),   # Dia cíclico (sin)
            math.cos(2 * math.pi * timestamp.weekday() / 7),   # Dia cíclico (cos)
            1 if timestamp.weekday() >= 5 else 0,              # Weekend flag
        ]

    def predict(
        self,
        gpu_name: str,
        machine_type: str = "on-demand",
    ) -> Optional[Dict]:
        """
        Gera previsões para as próximas 24 horas.

        Returns:
            Dict com previsões por hora e dia, ou None se modelo não existe
        """
        key = f"{gpu_name}:{machine_type}"

        # Verificar se modelo precisa ser treinado
        if key not in self.models:
            if not self.train_model(gpu_name, machine_type):
                return None

        if self._ml_available and key in self.scalers:
            return self._predict_ml(key, gpu_name, machine_type)
        else:
            return self._predict_simple(key, gpu_name, machine_type)

    def _predict_ml(self, key: str, gpu_name: str, machine_type: str) -> Optional[Dict]:
        """Gera previsões usando modelo ML."""
        try:
            import numpy as np

            model = self.models[key]
            scaler = self.scalers[key]

            now = datetime.utcnow()
            hourly_predictions = {}

            # Prever para cada hora das próximas 24h
            for hour_offset in range(24):
                future_time = now + timedelta(hours=hour_offset)
                features = self._extract_features(future_time)
                features_scaled = scaler.transform([features])
                prediction = model.predict(features_scaled)[0]
                hourly_predictions[str(future_time.hour)] = round(prediction, 4)

            # Prever média por dia da semana
            daily_predictions = {}
            day_names = ['monday', 'tuesday', 'wednesday', 'thursday',
                         'friday', 'saturday', 'sunday']

            for day in range(7):
                future_day = now + timedelta(days=day)
                day_name = day_names[future_day.weekday()]

                # Média das previsões desse dia
                day_prices = []
                for hour in range(24):
                    future_time = future_day.replace(hour=hour, minute=0, second=0)
                    features = self._extract_features(future_time)
                    features_scaled = scaler.transform([features])
                    prediction = model.predict(features_scaled)[0]
                    day_prices.append(prediction)

                daily_predictions[day_name] = round(statistics.mean(day_prices), 4)

            return self._build_prediction_result(
                gpu_name, machine_type, hourly_predictions, daily_predictions
            )

        except Exception as e:
            logger.error(f"Erro na previsão ML: {e}")
            return None

    def _predict_simple(self, key: str, gpu_name: str, machine_type: str) -> Optional[Dict]:
        """Gera previsões usando modelo simples."""
        try:
            model_data = self.models[key]
            hourly_avg = model_data['hourly']
            daily_avg = model_data['daily']
            overall_avg = model_data['overall_avg']

            # Previsões por hora
            hourly_predictions = {}
            for hour in range(24):
                price = hourly_avg.get(hour, overall_avg)
                hourly_predictions[str(hour)] = round(price, 4)

            # Previsões por dia
            day_names = ['monday', 'tuesday', 'wednesday', 'thursday',
                         'friday', 'saturday', 'sunday']
            daily_predictions = {}
            for day in range(7):
                price = daily_avg.get(day, overall_avg)
                daily_predictions[day_names[day]] = round(price, 4)

            return self._build_prediction_result(
                gpu_name, machine_type, hourly_predictions, daily_predictions
            )

        except Exception as e:
            logger.error(f"Erro na previsão simples: {e}")
            return None

    def _build_prediction_result(
        self,
        gpu_name: str,
        machine_type: str,
        hourly_predictions: Dict[str, float],
        daily_predictions: Dict[str, float],
    ) -> Dict:
        """Constrói resultado da previsão."""
        # Encontrar melhor horário
        best_hour = min(hourly_predictions.items(), key=lambda x: x[1])
        best_day = min(daily_predictions.items(), key=lambda x: x[1])

        # Calcular confiança
        confidence = self._calculate_confidence(gpu_name, machine_type)

        now = datetime.utcnow()
        return {
            'gpu_name': gpu_name,
            'machine_type': machine_type,
            'hourly_predictions': hourly_predictions,
            'daily_predictions': daily_predictions,
            'best_hour_utc': int(best_hour[0]),
            'best_day': best_day[0],
            'predicted_min_price': best_hour[1],
            'model_confidence': confidence,
            'model_version': self.MODEL_VERSION,
            'valid_until': (now + timedelta(hours=6)).isoformat(),
            'created_at': now.isoformat(),
        }

    def _calculate_confidence(
        self,
        gpu_name: str,
        machine_type: str
    ) -> float:
        """Calcula confiança do modelo baseado em variância histórica."""
        db = SessionLocal()
        try:
            # Últimos 7 dias
            start_time = datetime.utcnow() - timedelta(days=7)
            records = db.query(MarketSnapshot).filter(
                MarketSnapshot.gpu_name == gpu_name,
                MarketSnapshot.machine_type == machine_type,
                MarketSnapshot.timestamp >= start_time,
            ).all()

            if len(records) < 10:
                return 0.5

            prices = [r.avg_price for r in records if r.avg_price > 0]
            if not prices or len(prices) < 2:
                return 0.5

            # Coeficiente de variação
            mean_price = statistics.mean(prices)
            if mean_price <= 0:
                return 0.5

            cv = statistics.stdev(prices) / mean_price

            # Quanto menor a variação, maior a confiança
            confidence = max(0.3, min(0.95, 1 - cv))
            return round(confidence, 2)

        except Exception as e:
            logger.error(f"Erro ao calcular confiança: {e}")
            return 0.5
        finally:
            db.close()

    def save_prediction(self, prediction: Dict) -> bool:
        """Salva previsão no banco de dados."""
        db = SessionLocal()
        try:
            day_names = ['monday', 'tuesday', 'wednesday', 'thursday',
                         'friday', 'saturday', 'sunday']

            record = PricePrediction(
                created_at=datetime.utcnow(),
                gpu_name=prediction['gpu_name'],
                machine_type=prediction['machine_type'],
                predictions_hourly=prediction['hourly_predictions'],
                predictions_daily=prediction['daily_predictions'],
                model_confidence=prediction['model_confidence'],
                model_version=prediction['model_version'],
                best_hour_utc=prediction['best_hour_utc'],
                best_day_of_week=day_names.index(prediction['best_day']),
                predicted_min_price=prediction['predicted_min_price'],
                valid_until=datetime.fromisoformat(prediction['valid_until']),
            )
            db.add(record)
            db.commit()
            logger.info(f"Previsão salva para {prediction['gpu_name']}")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar previsão: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    def get_latest_prediction(
        self,
        gpu_name: str,
        machine_type: str = "on-demand"
    ) -> Optional[Dict]:
        """Busca última previsão válida do banco."""
        db = SessionLocal()
        try:
            record = db.query(PricePrediction).filter(
                PricePrediction.gpu_name == gpu_name,
                PricePrediction.machine_type == machine_type,
                PricePrediction.valid_until >= datetime.utcnow(),
            ).order_by(PricePrediction.created_at.desc()).first()

            if not record:
                return None

            day_names = ['monday', 'tuesday', 'wednesday', 'thursday',
                         'friday', 'saturday', 'sunday']

            return {
                'gpu_name': record.gpu_name,
                'machine_type': record.machine_type,
                'hourly_predictions': record.predictions_hourly,
                'daily_predictions': record.predictions_daily,
                'best_hour_utc': record.best_hour_utc,
                'best_day': day_names[record.best_day_of_week] if record.best_day_of_week is not None else 'unknown',
                'predicted_min_price': record.predicted_min_price,
                'model_confidence': record.model_confidence,
                'model_version': record.model_version,
                'valid_until': record.valid_until.isoformat() if record.valid_until else '',
                'created_at': record.created_at.isoformat() if record.created_at else None,
            }
        except Exception as e:
            logger.error(f"Erro ao buscar previsão: {e}")
            return None
        finally:
            db.close()

    def generate_all_predictions(
        self,
        gpus: List[str],
        machine_types: List[str] = None
    ) -> int:
        """
        Gera previsões para todas as GPUs e tipos especificados.

        Returns:
            Número de previsões geradas com sucesso
        """
        machine_types = machine_types or ["on-demand", "interruptible"]
        count = 0

        for gpu_name in gpus:
            for machine_type in machine_types:
                try:
                    prediction = self.predict(gpu_name, machine_type)
                    if prediction:
                        if self.save_prediction(prediction):
                            count += 1
                except Exception as e:
                    logger.warning(f"Falha ao gerar previsão para {gpu_name}:{machine_type}: {e}")

        logger.info(f"Geradas {count} previsões")
        return count

    def forecast_costs_7day(
        self,
        gpu_name: str,
        machine_type: str = "on-demand",
        hours_per_day: float = 24.0,
    ) -> Optional[List[Dict]]:
        """
        Gera previsão de custos para os próximos 7 dias.

        Retorna previsões horárias agregadas por dia com intervalos de confiança.

        Args:
            gpu_name: Nome da GPU
            machine_type: Tipo de máquina (on-demand ou interruptible)
            hours_per_day: Horas de uso por dia para cálculo de custo

        Returns:
            Lista de dicts com previsões diárias:
            [
                {
                    "day": "2024-01-15",
                    "forecasted_cost": 12.50,
                    "confidence_interval": [11.20, 13.80],
                    "hourly_predictions": [...]
                },
                ...
            ]
            Retorna None se não houver dados suficientes para treinar modelo.
        """
        key = f"{gpu_name}:{machine_type}"

        # Verificar/treinar modelo
        if key not in self.models:
            if not self.train_model(gpu_name, machine_type):
                logger.warning(f"Dados insuficientes para forecast 7-day: {key}")
                return None

        if self._ml_available and key in self.scalers:
            return self._forecast_7day_ml(key, gpu_name, machine_type, hours_per_day)
        else:
            return self._forecast_7day_simple(key, gpu_name, machine_type, hours_per_day)

    def _forecast_7day_ml(
        self,
        key: str,
        gpu_name: str,
        machine_type: str,
        hours_per_day: float,
    ) -> Optional[List[Dict]]:
        """Gera forecast de 7 dias usando modelo ML com intervalos de confiança."""
        try:
            import numpy as np

            model = self.models[key]
            scaler = self.scalers[key]

            now = datetime.utcnow()
            daily_forecasts = []

            for day_offset in range(7):
                day_start = (now + timedelta(days=day_offset)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                day_date = day_start.strftime("%Y-%m-%d")

                hourly_predictions = []
                all_tree_predictions = []

                # Prever para cada hora do dia
                for hour in range(24):
                    future_time = day_start + timedelta(hours=hour)
                    features = self._extract_features(future_time)
                    features_scaled = scaler.transform([features])

                    # Previsão principal
                    prediction = model.predict(features_scaled)[0]
                    hourly_predictions.append({
                        "hour": hour,
                        "timestamp": future_time.isoformat(),
                        "price": round(prediction, 4),
                    })

                    # Coletar previsões de cada árvore para intervalo de confiança
                    tree_preds = [
                        tree.predict(features_scaled)[0]
                        for tree in model.estimators_
                    ]
                    all_tree_predictions.append(tree_preds)

                # Calcular custo diário e intervalo de confiança
                avg_price = statistics.mean([p["price"] for p in hourly_predictions])
                daily_cost = avg_price * hours_per_day

                # Intervalo de confiança baseado nas previsões das árvores
                all_preds_flat = [p for hour_preds in all_tree_predictions for p in hour_preds]
                if len(all_preds_flat) >= 2:
                    std_dev = statistics.stdev(all_preds_flat)
                    # 95% confidence interval (1.96 sigma), capped at 3 sigma
                    margin = min(1.96 * std_dev * hours_per_day, 3 * std_dev * hours_per_day)
                    lower_bound = max(0, daily_cost - margin)
                    upper_bound = daily_cost + margin
                else:
                    lower_bound = daily_cost * 0.9
                    upper_bound = daily_cost * 1.1

                daily_forecasts.append({
                    "day": day_date,
                    "forecasted_cost": round(daily_cost, 2),
                    "confidence_interval": [
                        round(lower_bound, 2),
                        round(upper_bound, 2),
                    ],
                    "avg_hourly_price": round(avg_price, 4),
                    "hourly_predictions": hourly_predictions,
                    "gpu_name": gpu_name,
                    "machine_type": machine_type,
                })

            logger.info(f"Forecast 7-day gerado para {key}")
            return daily_forecasts

        except Exception as e:
            logger.error(f"Erro no forecast ML 7-day: {e}")
            return None

    def _forecast_7day_simple(
        self,
        key: str,
        gpu_name: str,
        machine_type: str,
        hours_per_day: float,
    ) -> Optional[List[Dict]]:
        """Gera forecast de 7 dias usando modelo simples baseado em médias."""
        try:
            model_data = self.models[key]
            hourly_avg = model_data['hourly']
            daily_avg = model_data['daily']
            overall_avg = model_data['overall_avg']

            now = datetime.utcnow()
            daily_forecasts = []

            for day_offset in range(7):
                day_start = (now + timedelta(days=day_offset)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                day_date = day_start.strftime("%Y-%m-%d")
                day_of_week = day_start.weekday()

                hourly_predictions = []

                # Prever para cada hora do dia
                for hour in range(24):
                    future_time = day_start + timedelta(hours=hour)
                    price = hourly_avg.get(hour, overall_avg)
                    hourly_predictions.append({
                        "hour": hour,
                        "timestamp": future_time.isoformat(),
                        "price": round(price, 4),
                    })

                # Custo diário baseado na média do dia da semana
                day_avg_price = daily_avg.get(day_of_week, overall_avg)
                daily_cost = day_avg_price * hours_per_day

                # Intervalo de confiança simples (±10% para modelo simples)
                margin = daily_cost * 0.1
                lower_bound = max(0, daily_cost - margin)
                upper_bound = daily_cost + margin

                daily_forecasts.append({
                    "day": day_date,
                    "forecasted_cost": round(daily_cost, 2),
                    "confidence_interval": [
                        round(lower_bound, 2),
                        round(upper_bound, 2),
                    ],
                    "avg_hourly_price": round(day_avg_price, 4),
                    "hourly_predictions": hourly_predictions,
                    "gpu_name": gpu_name,
                    "machine_type": machine_type,
                })

            logger.info(f"Forecast 7-day simples gerado para {key}")
            return daily_forecasts

        except Exception as e:
            logger.error(f"Erro no forecast simples 7-day: {e}")
            return None
