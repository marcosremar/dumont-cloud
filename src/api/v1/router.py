"""
Main API v1 router
"""
from fastapi import APIRouter

from .endpoints import auth, instances, snapshots, settings, metrics, ai_wizard, standby, agent, savings, advisor, hibernation, finetune, chat, reports
from .endpoints import auth, oidc, instances, snapshots, settings, metrics, ai_wizard, standby, agent, savings, advisor, hibernation, finetune, chat
from .endpoints import warmpool, failover_settings, failover, serverless, spot_deploy, machine_history, jobs, models
from .endpoints import market, hosts, templates
from .endpoints import market, hosts
from .endpoints import email_preferences, unsubscribe
from .endpoints import market, hosts, nps
from .endpoints import market, hosts, webhooks
from .endpoints import market, hosts, currency
from .endpoints import market, hosts, teams, roles, users
from . import audit
from .endpoints import market, hosts, reservations
from .endpoints.settings import balance_router
from .endpoints.spot import router as spot_router
from .endpoints.metrics import reliability_router

# Create API v1 router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router)

# OIDC SSO - Enterprise Single Sign-On via OpenID Connect
api_router.include_router(oidc.router)
api_router.include_router(instances.public_router)  # Public endpoints first (no auth required)
api_router.include_router(instances.router)
api_router.include_router(snapshots.router)
api_router.include_router(settings.router)
api_router.include_router(balance_router)
api_router.include_router(metrics.router)
api_router.include_router(ai_wizard.router)
api_router.include_router(advisor.router, prefix="/advisor", tags=["AI GPU Advisor"])
api_router.include_router(hibernation.router, prefix="/hibernation", tags=["Auto-Hibernation"])
api_router.include_router(standby.router)
api_router.include_router(agent.router)
api_router.include_router(savings.router, prefix="/savings", tags=["Savings Dashboard"])
api_router.include_router(reports.router, prefix="/reports", tags=["Shareable Reports"])
api_router.include_router(finetune.router)

# Spot Reports - Relatórios de instâncias spot
api_router.include_router(spot_router, prefix="/metrics", tags=["Spot Reports"])

# GPU Warm Pool - Estratégia principal de failover
api_router.include_router(warmpool.router, tags=["GPU Warm Pool"])

# Failover Settings - Configurações de failover
api_router.include_router(failover_settings.router, tags=["Failover Settings"])

# Failover Orchestrator - Execução de failover
api_router.include_router(failover.router, tags=["Failover Orchestrator"])

# Serverless GPU - Auto-pause/resume
api_router.include_router(serverless.router, tags=["Serverless GPU"])
api_router.include_router(serverless.public_router, tags=["Serverless GPU"])  # Public endpoints (no auth)

# Spot GPU Deploy - Deploy e failover de instâncias spot
api_router.include_router(spot_deploy.router, tags=["Spot GPU Deploy"])

# Chat - LLM Chat Integration
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])

# Machine History & Blacklist - Histórico de máquinas e blacklist
api_router.include_router(machine_history.router, tags=["Machine History"])

# Jobs - GPU Jobs (Execute and Destroy)
api_router.include_router(jobs.router, tags=["Jobs"])

# Models - Deploy and manage ML models (LLM, Whisper, Diffusion, Embeddings)
api_router.include_router(models.router, tags=["Models"])

# Market - Price prediction and market analysis
api_router.include_router(market.router, tags=["Market"])

# Hosts - Host management and blacklist
api_router.include_router(hosts.router, tags=["Hosts"])

# Templates - ML Workload Template Marketplace
api_router.include_router(templates.router, tags=["Templates"])

# Machine Reliability - Reliability scores and user ratings
api_router.include_router(reliability_router, tags=["Machine Reliability"])
# Email Preferences - User email report settings
api_router.include_router(email_preferences.router, tags=["Email Preferences"])

# Unsubscribe - One-click email unsubscribe (no auth required per CAN-SPAM)
api_router.include_router(unsubscribe.router, tags=["Unsubscribe"])
# NPS - Net Promoter Score surveys
api_router.include_router(nps.router, tags=["NPS"])
# Webhooks - Webhook configuration and delivery
api_router.include_router(webhooks.router, tags=["Webhooks"])
# Currency - Multi-currency pricing support
api_router.include_router(currency.router, tags=["Currency"])
# Teams - Team management and RBAC
api_router.include_router(teams.router, tags=["Teams"])

# Roles & Permissions - RBAC role and permission management
api_router.include_router(roles.router, tags=["Roles & Permissions"])

# Audit Logs - Team audit logging for compliance and security
api_router.include_router(audit.router, tags=["Audit Logs"])

# Users - User profile and team context switching
api_router.include_router(users.router, tags=["Users"])
# GPU Reservations - Reserve GPU capacity with guaranteed availability
api_router.include_router(reservations.router, tags=["Reservations"])
