"""
Script para popular dados históricos de uptime a partir de MachineStats e MachineAttempt.

Este script:
1. Consulta MachineStats para obter lista de máquinas conhecidas
2. Consulta MachineAttempt para obter tentativas dos últimos 30 dias
3. Calcula uptime diário e contagem de interrupções
4. Popula a tabela MachineUptimeHistory
"""
import sys
import os
from datetime import datetime, timedelta
from collections import defaultdict

# Adiciona o diretório raiz ao path para importar os módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.database import SessionLocal, engine, Base
from src.models.machine_history import (
    MachineStats,
    MachineAttempt,
    MachineUptimeHistory
)

# Número de dias para gerar histórico
HISTORY_DAYS = 30

# Segundos em um dia
SECONDS_PER_DAY = 86400


def get_date_range(days: int = HISTORY_DAYS) -> list:
    """Retorna lista de datas para os últimos N dias."""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return [today - timedelta(days=i) for i in range(days)]


def calculate_daily_stats(attempts: list, date: datetime) -> dict:
    """
    Calcula estatísticas diárias a partir de tentativas.

    Args:
        attempts: Lista de MachineAttempt do dia
        date: Data do dia

    Returns:
        Dict com estatísticas calculadas
    """
    total = len(attempts)
    successful = sum(1 for a in attempts if a.success)
    failed = total - successful

    # Calcular uptime baseado na taxa de sucesso
    # Se não há tentativas, assume 95% (máquina pode estar boa mas não testada)
    if total == 0:
        uptime_percentage = 95.0
    else:
        # Taxa de sucesso das tentativas convertida para uptime
        uptime_percentage = (successful / total) * 100.0

    # Contar interrupções (transições de sucesso para falha)
    interruption_count = 0
    sorted_attempts = sorted(attempts, key=lambda x: x.attempted_at)
    last_success = None
    for attempt in sorted_attempts:
        if last_success is True and not attempt.success:
            interruption_count += 1
        last_success = attempt.success

    # Calcular duração média das interrupções
    avg_interruption_duration = None
    if failed > 0:
        failure_durations = [
            a.time_to_failure_seconds
            for a in attempts
            if not a.success and a.time_to_failure_seconds
        ]
        if failure_durations:
            avg_interruption_duration = sum(failure_durations) / len(failure_durations)

    return {
        "uptime_percentage": round(uptime_percentage, 2),
        "uptime_seconds": int(uptime_percentage / 100.0 * SECONDS_PER_DAY),
        "total_seconds": SECONDS_PER_DAY,
        "interruption_count": interruption_count,
        "avg_interruption_duration_seconds": avg_interruption_duration,
        "total_attempts": total,
        "successful_attempts": successful,
        "failed_attempts": failed,
    }


def populate_uptime_history():
    """
    Popula dados históricos de uptime para todas as máquinas conhecidas.
    """
    db = SessionLocal()

    try:
        print("=" * 60)
        print("Populando histórico de uptime de máquinas")
        print("=" * 60)

        # Obter lista de máquinas do MachineStats
        machines = db.query(MachineStats).all()
        print(f"\nEncontradas {len(machines)} máquinas em MachineStats")

        if not machines:
            print("Nenhuma máquina encontrada. Verificando MachineAttempt...")
            # Obter máquinas únicas de MachineAttempt
            attempts = db.query(
                MachineAttempt.provider,
                MachineAttempt.machine_id,
                MachineAttempt.gpu_name
            ).distinct().all()

            if not attempts:
                print("Nenhuma tentativa encontrada. Criando dados de demonstração...")
                machines = create_demo_data(db)
            else:
                # Criar entradas para cada máquina única
                machines = []
                for provider, machine_id, gpu_name in attempts:
                    machines.append({
                        "provider": provider,
                        "machine_id": machine_id,
                        "gpu_name": gpu_name
                    })
                print(f"Encontradas {len(machines)} máquinas únicas em MachineAttempt")

        # Período de histórico
        dates = get_date_range(HISTORY_DAYS)
        start_date = min(dates)
        print(f"Gerando histórico de {start_date.strftime('%Y-%m-%d')} até hoje")

        records_created = 0
        records_updated = 0

        for machine in machines:
            # Suporte para MachineStats e dict
            if isinstance(machine, dict):
                provider = machine["provider"]
                machine_id = machine["machine_id"]
                gpu_name = machine.get("gpu_name")
            else:
                provider = machine.provider
                machine_id = machine.machine_id
                gpu_name = machine.gpu_name

            print(f"\nProcessando {provider}:{machine_id}...")

            # Obter tentativas desta máquina nos últimos 30 dias
            attempts = db.query(MachineAttempt).filter(
                MachineAttempt.provider == provider,
                MachineAttempt.machine_id == machine_id,
                MachineAttempt.attempted_at >= start_date
            ).all()

            # Agrupar tentativas por dia
            attempts_by_day = defaultdict(list)
            for attempt in attempts:
                day = attempt.attempted_at.replace(hour=0, minute=0, second=0, microsecond=0)
                attempts_by_day[day].append(attempt)

            # Criar registro de uptime para cada dia
            for date in dates:
                day_attempts = attempts_by_day.get(date, [])
                stats = calculate_daily_stats(day_attempts, date)

                # Verificar se já existe registro para este dia
                existing = db.query(MachineUptimeHistory).filter(
                    MachineUptimeHistory.provider == provider,
                    MachineUptimeHistory.machine_id == machine_id,
                    MachineUptimeHistory.date == date
                ).first()

                if existing:
                    # Atualizar registro existente
                    existing.uptime_percentage = stats["uptime_percentage"]
                    existing.uptime_seconds = stats["uptime_seconds"]
                    existing.total_seconds = stats["total_seconds"]
                    existing.interruption_count = stats["interruption_count"]
                    existing.avg_interruption_duration_seconds = stats["avg_interruption_duration_seconds"]
                    existing.total_attempts = stats["total_attempts"]
                    existing.successful_attempts = stats["successful_attempts"]
                    existing.failed_attempts = stats["failed_attempts"]
                    existing.gpu_name = gpu_name
                    existing.updated_at = datetime.utcnow()
                    records_updated += 1
                else:
                    # Criar novo registro
                    history = MachineUptimeHistory(
                        provider=provider,
                        machine_id=machine_id,
                        date=date,
                        uptime_percentage=stats["uptime_percentage"],
                        uptime_seconds=stats["uptime_seconds"],
                        total_seconds=stats["total_seconds"],
                        interruption_count=stats["interruption_count"],
                        avg_interruption_duration_seconds=stats["avg_interruption_duration_seconds"],
                        total_attempts=stats["total_attempts"],
                        successful_attempts=stats["successful_attempts"],
                        failed_attempts=stats["failed_attempts"],
                        gpu_name=gpu_name,
                    )
                    db.add(history)
                    records_created += 1

        db.commit()

        print("\n" + "=" * 60)
        print(f"✅ Histórico de uptime populado com sucesso!")
        print(f"   Registros criados: {records_created}")
        print(f"   Registros atualizados: {records_updated}")
        print("=" * 60)

        # Mostrar estatísticas finais
        total_records = db.query(MachineUptimeHistory).count()
        print(f"\nTotal de registros em machine_uptime_history: {total_records}")

        return True

    except Exception as e:
        print(f"\n❌ Erro ao popular histórico: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
        return False

    finally:
        db.close()


def create_demo_data(db) -> list:
    """
    Cria dados de demonstração se não houver máquinas reais.

    Cria 5 máquinas de exemplo com dados variados de uptime
    para permitir testes da funcionalidade.
    """
    import random

    demo_machines = [
        {"provider": "vast", "machine_id": "demo_1", "gpu_name": "RTX 4090", "base_uptime": 98.0},
        {"provider": "vast", "machine_id": "demo_2", "gpu_name": "RTX 3090", "base_uptime": 92.0},
        {"provider": "vast", "machine_id": "demo_3", "gpu_name": "A100 80GB", "base_uptime": 99.5},
        {"provider": "tensordock", "machine_id": "demo_4", "gpu_name": "RTX 4080", "base_uptime": 85.0},
        {"provider": "tensordock", "machine_id": "demo_5", "gpu_name": "H100", "base_uptime": 97.0},
    ]

    print(f"Criando {len(demo_machines)} máquinas de demonstração...")

    dates = get_date_range(HISTORY_DAYS)

    for machine in demo_machines:
        provider = machine["provider"]
        machine_id = machine["machine_id"]
        gpu_name = machine["gpu_name"]
        base_uptime = machine["base_uptime"]

        for date in dates:
            # Variar uptime em ±5% do base
            uptime = min(100.0, max(0.0, base_uptime + random.uniform(-5, 5)))

            # Calcular interrupções baseado no uptime (menos uptime = mais interrupções)
            interruption_count = max(0, int((100 - uptime) / 10))

            # Algumas tentativas por dia
            total_attempts = random.randint(0, 5)
            successful_attempts = int(total_attempts * uptime / 100)
            failed_attempts = total_attempts - successful_attempts

            history = MachineUptimeHistory(
                provider=provider,
                machine_id=machine_id,
                date=date,
                uptime_percentage=round(uptime, 2),
                uptime_seconds=int(uptime / 100 * SECONDS_PER_DAY),
                total_seconds=SECONDS_PER_DAY,
                interruption_count=interruption_count,
                avg_interruption_duration_seconds=random.uniform(30, 300) if interruption_count > 0 else None,
                total_attempts=total_attempts,
                successful_attempts=successful_attempts,
                failed_attempts=failed_attempts,
                gpu_name=gpu_name,
            )
            db.add(history)

    db.commit()
    print(f"✅ Dados de demonstração criados!")

    return demo_machines


if __name__ == "__main__":
    # Criar tabelas se não existirem
    Base.metadata.create_all(bind=engine)

    # Popular histórico
    success = populate_uptime_history()
    sys.exit(0 if success else 1)
