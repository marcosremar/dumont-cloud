# Sprint 4 - MVP Polish

**Periodo**: 19/12/2024 - 02/01/2025 | **Status**: Em Andamento

---

## UI/UX

### [x] Migrar componentes para Dumont UI Design System
**Contexto**: Interface usava componentes inconsistentes. Adotamos TailAdmin como base para Dumont UI.
**Arquivos**: `web/src/components/ui/dumont-ui.jsx`

### [x] Implementar tema consistente
**Contexto**: Paleta oficial verde (#2ea043), tipografia Inter/Merriweather.
**Arquivos**: `web/src/index.css`, `tailwind.config.js`

### [x] Criar documentacao Live Docs
**Contexto**: Sistema integrado ao FastAPI em `/admin/doc/live` com markdown e Mermaid.
**Arquivos**: `src/main.py`, `src/templates/marketing_doc.html`

### [x] Pesquisa de concorrentes
**Contexto**: Analise de Vast.ai, RunPod, Lambda Labs para definir UX.
**Resultado**: "Simplicidade do RunPod + Precos do Vast.ai + Failover automatico"

### [ ] Redesenhar cards de maquinas
**Contexto**: Cards devem mostrar status (cor), GPU/RAM/Disk, custo/hora, uptime, botoes de acao.
**Por que**: Usuarios querem ver metricas rapido. RunPod e Vast.ai usam cards informativos.
**Arquivos**: `web/src/pages/Machines.jsx`, `web/src/components/MachineCard.jsx`

### [ ] Implementar empty states
**Contexto**: Tela vazia deve guiar usuario para proxima acao com CTA.
**Por que**: Nunca deixar tela vazia. Oportunidade de converter.
**Arquivos**: `web/src/components/EmptyState.jsx`, `web/src/pages/Machines.jsx`

### [ ] Adicionar loading skeletons
**Contexto**: Skeletons reduzem percepcao de espera em 30%.
**Arquivos**: `web/src/components/Skeleton.jsx`

### [ ] Melhorar responsividade mobile
**Contexto**: 30% dos acessos vem de mobile. Sidebar colapsavel, cards em stack.
**Arquivos**: `web/src/components/Sidebar.jsx`, `web/src/pages/*.jsx`

---

## Backend

### [x] CPU Standby - 62 testes passando
**Contexto**: Pausar GPU cara, manter CPU barata. Diferencial competitivo.
**Arquivos**: `src/services/cpu_standby.py`

### [x] API endpoints para Live Docs
**Contexto**: `/api/menu` e `/api/content` para documentacao dinamica.
**Arquivos**: `src/main.py`

### [ ] Otimizar queries de billing
**Contexto**: Query atual faz N+1. Usar JOIN e paginacao.
**Por que**: Billing demora 3-5s. Usuario precisa ver saldo rapido.
**Arquivos**: `src/services/billing.py`

### [ ] Cache de metricas GPU
**Contexto**: Redis cache TTL 10s para nao sobrecarregar API externa.
**Por que**: Dashboard atualiza a cada 5s. Sem cache = lento.
**Arquivos**: `src/services/gpu_metrics.py`, `src/core/cache.py`

### [ ] Rate limiting
**Contexto**: API vulneravel a abuso. Limitar por IP/user.
**Por que**: Seguranca basica contra DDoS e scraping.
**Arquivos**: `src/middleware/rate_limit.py`

---

## Templates

### [ ] Template PyTorch
**Contexto**: Framework ML mais popular (60% market share). PyTorch + CUDA + Jupyter.
**Por que**: Primeiro template que usuarios procuram. Essencial para MVP.
**Arquivos**: `src/templates/pytorch.yaml`

### [ ] Template TensorFlow
**Contexto**: Segundo framework mais usado. TF + CUDA + Jupyter + TensorBoard.
**Por que**: Complementa PyTorch. Enterprise e academico.
**Arquivos**: `src/templates/tensorflow.yaml`

### [ ] Template ComfyUI
**Contexto**: Interface mais popular para Stable Diffusion. AI Art.
**Por que**: Mercado cresce 200% ao ano. Vast.ai e RunPod destacam.
**Arquivos**: `src/templates/comfyui.yaml`

### [ ] Template Ollama
**Contexto**: Rodar LLMs localmente (Llama, Mistral). Open WebUI.
**Por que**: Alternativa a OpenAI. Privacidade. Prototipacao.
**Arquivos**: `src/templates/ollama.yaml`

### [ ] Sistema de one-click deploy
**Contexto**: Seleciona template -> escolhe GPU -> clica Launch. Sem config manual.
**Por que**: "Time to First GPU" < 5 min. RunPod se destaca por isso.
**Arquivos**: `src/services/one_click_deploy.py`, `web/src/components/LaunchWizard.jsx`

---

## Testes

### [ ] Testes E2E - New User Journey
**Contexto**: signup -> add credits -> launch GPU -> connect -> stop
**Arquivos**: `tests/e2e-journeys/new-user-journey.spec.js`

### [ ] Testes E2E - Admin Journey
**Contexto**: login admin -> view users -> impersonate -> logs
**Arquivos**: `tests/e2e-journeys/admin-journey.spec.js`

### [ ] Testes E2E - ML Researcher Journey
**Contexto**: launch PyTorch -> Jupyter -> run training -> GPU metrics -> stop
**Arquivos**: `tests/e2e-journeys/ml-researcher-journey.spec.js`

### [ ] Testes de contrato API
**Contexto**: Validar schemas request/response automaticamente.
**Arquivos**: `tests/contract/test_api_contracts.py`

### [ ] Coverage > 80%
**Contexto**: Cobertura atual ~65%. Meta 80% para beta.
**Arquivos**: `tests/unit/`, `tests/integration/`

---

## Documentacao

### [x] Live Docs funcionando
### [x] Guia de MVP Layout
### [x] Analise de Concorrentes
### [x] Pricing documentado

### [ ] API Reference completa
**Contexto**: Falta exemplos e explicacoes nos endpoints.
**Arquivos**: `Live-Doc/content/04_API/`

### [ ] Guia de Onboarding
**Contexto**: Passo-a-passo para novos usuarios.
**Arquivos**: `Live-Doc/content/01_Getting_Started/04_Onboarding_Guide.md`

---

## Checklist Rapido

### Concluido
- [x] Dumont UI Design System
- [x] Tema consistente
- [x] Live Docs
- [x] Pesquisa concorrentes
- [x] CPU Standby (62 testes)
- [x] API Live Docs

### Pendente - Prioridade Alta
- [ ] Cards de maquinas
- [ ] Template PyTorch
- [ ] Template ComfyUI
- [ ] One-click deploy
- [ ] Testes E2E New User

### Pendente - Prioridade Media
- [ ] Empty states
- [ ] Loading skeletons
- [ ] Cache metricas GPU
- [ ] Rate limiting
- [ ] API Reference

### Pendente - Prioridade Baixa
- [ ] Responsividade mobile
- [ ] Template TensorFlow
- [ ] Template Ollama
- [ ] Testes Admin/ML Researcher
- [ ] Coverage 80%
