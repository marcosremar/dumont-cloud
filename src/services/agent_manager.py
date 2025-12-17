"""
Sistema de gerenciamento de agentes com auto-restart.

Este módulo gerencia agentes que rodam em background, reiniciando-os
automaticamente em caso de falha.
"""

import threading
import time
import logging
from typing import Dict, Type, List
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class Agent(ABC):
    """Classe base para agentes que rodam em background."""

    def __init__(self, name: str):
        self.name = name
        self.running = False
        self.thread = None
        self._stop_event = threading.Event()

    @abstractmethod
    def run(self):
        """Lógica principal do agente. Deve ser implementado pelas subclasses."""
        pass

    def start(self):
        """Inicia o agente em uma thread separada."""
        if self.running:
            logger.warning(f"Agente {self.name} já está rodando")
            return

        self.running = True
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._run_with_restart, daemon=True)
        self.thread.start()
        logger.info(f"Agente {self.name} iniciado")

    def stop(self):
        """Para o agente."""
        logger.info(f"Parando agente {self.name}")
        self.running = False
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)

    def _run_with_restart(self):
        """Executa o agente com auto-restart em caso de falha."""
        restart_delay = 5  # segundos entre restarts

        while self.running:
            try:
                logger.info(f"Iniciando execução do agente {self.name}")
                self.run()
            except Exception as e:
                logger.error(f"Erro no agente {self.name}: {e}", exc_info=True)

                if self.running:
                    logger.info(f"Reiniciando agente {self.name} em {restart_delay} segundos...")
                    time.sleep(restart_delay)
                else:
                    break

    def is_running(self) -> bool:
        """Verifica se o agente está rodando."""
        return self.running and self.thread and self.thread.is_alive()

    def sleep(self, seconds: float):
        """Sleep interrompível para permitir shutdown rápido."""
        self._stop_event.wait(timeout=seconds)


class AgentManager:
    """Gerenciador central de todos os agentes."""

    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        logger.info("AgentManager inicializado")

    def register_agent(self, agent_class: Type[Agent], *args, **kwargs):
        """Registra e inicia um novo agente."""
        agent = agent_class(*args, **kwargs)
        self.agents[agent.name] = agent
        agent.start()
        logger.info(f"Agente {agent.name} registrado e iniciado")
        return agent

    def stop_agent(self, name: str):
        """Para um agente específico."""
        if name in self.agents:
            self.agents[name].stop()
            del self.agents[name]
            logger.info(f"Agente {name} parado e removido")

    def stop_all(self):
        """Para todos os agentes."""
        logger.info("Parando todos os agentes...")
        for name, agent in list(self.agents.items()):
            agent.stop()
        self.agents.clear()
        logger.info("Todos os agentes parados")

    def get_status(self) -> List[Dict]:
        """Retorna status de todos os agentes."""
        return [
            {
                "name": name,
                "running": agent.is_running(),
                "class": agent.__class__.__name__
            }
            for name, agent in self.agents.items()
        ]

    def restart_agent(self, name: str):
        """Reinicia um agente específico."""
        if name in self.agents:
            agent = self.agents[name]
            agent.stop()
            time.sleep(1)
            agent.start()
            logger.info(f"Agente {name} reiniciado")


# Instância global do gerenciador
agent_manager = AgentManager()
