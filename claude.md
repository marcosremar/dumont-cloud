# Dumont Cloud - Sistema de Gerenciamento de GPU Cloud

## Objetivo Principal

Sistema de backup/restore ultra-rápido para ambientes de GPU cloud (vast.ai, runpod, etc).
**O tempo de inicialização é crítico** - o sistema deve restaurar o ambiente de trabalho o mais rápido possível.

## Princípios de Design

### 1. Velocidade é Prioridade #1
- Cada segundo conta na inicialização
- Preferir soluções que minimizem latência
- Paralelizar operações sempre que possível

### 2. Timeout Agressivo de 10 Segundos por Etapa
- **REGRA CRÍTICA**: Cada etapa de inicialização tem timeout máximo de 10 segundos
- Se qualquer etapa demorar mais de 10s, a máquina é considerada lenta e deve ser:
  1. Imediatamente destruída
  2. Substituída por outra oferta disponível
- Etapas monitoradas:
  1. Criação da instância (API vast.ai)
  2. Instância ficar "running" com SSH disponível
  3. Conexão SSH estabelecida
  4. Instalação do restic
  5. Restore dos dados (timeout maior: 120s)

### 3. Estratégia de Multi-Start para Máquinas
- Máquinas GPU cloud têm tempos de inicialização imprevisíveis (10s a 3+ min)
- **Solução**: Iniciar múltiplas máquinas em paralelo, usar a primeira que ficar pronta
- Algoritmo:
  1. Iniciar 5 máquinas simultaneamente
  2. Aguardar 10 segundos
  3. Se nenhuma estiver pronta, iniciar mais 5 diferentes
  4. Repetir até 3 vezes (máximo 15 máquinas)
  5. Usar a primeira que responder, cancelar as outras

### 4. Restore Otimizado
- Usar restic com máximo de conexões paralelas (32+)
- Considerar cache local para arquivos frequentes
- Priorizar restauração de arquivos críticos primeiro

## Arquitetura

```
VPS (54.37.225.188)           GPU Cloud (vast.ai)
┌─────────────────┐           ┌─────────────────┐
│ Dashboard       │           │ Workspace       │
│ - Flask API     │◄─────────►│ - MuseTalk1.5   │
│ - Restic client │           │ - Sync daemon   │
└────────┬────────┘           └─────────────────┘
         │
         ▼
┌─────────────────┐
│ Cloudflare R2   │
│ - Restic repo   │
│ - ~7GB comprim. │
└─────────────────┘
```

## APIs Principais

- `/api/snapshots` - Lista snapshots com deduplicação por tree hash
- `/api/offers` - Lista máquinas disponíveis com filtros completos
- `/api/create-instance` - Cria instância vast.ai
- `/api/restore` - Restaura snapshot na máquina

## Credenciais (Desenvolvimento)

- VPS: ubuntu@54.37.225.188
- Dashboard: http://vps-a84d392b.vps.ovh.net:8765/
- R2 Bucket: musetalk
- Restic repo: s3:https://....r2.cloudflarestorage.com/musetalk/restic

## Boas Práticas de Desenvolvimento

### Execução de Comandos SSH

**IMPORTANTE**: Evitar comandos inline complexos que podem travar o terminal.

#### ❌ NÃO FAZER:
```bash
# Comandos longos inline que podem travar o terminal
ssh ubuntu@54.37.225.188 'ps aux | grep "python3 app" | grep -v grep && killall -9 python3 2>/dev/null; sleep 2; cd ~/dumont-cloud && python3 app.py > /tmp/app.log 2>&1 & sleep 3...'
```

#### ✅ FAZER:
```bash
# Criar script temporário e executar
cat > /tmp/deploy.sh << 'EOF'
#!/bin/bash
killall python3 2>/dev/null
sleep 1
cd ~/dumont-cloud
nohup python3 app.py > /tmp/app.log 2>&1 &
sleep 2
ps aux | grep "python3 app" | grep -v grep
EOF

scp /tmp/deploy.sh ubuntu@54.37.225.188:/tmp/
ssh ubuntu@54.37.225.188 'bash /tmp/deploy.sh'
```

**Razões**:
- Comandos inline longos podem bloquear o terminal
- Scripts separados são mais fáceis de debugar
- Melhor controle sobre timeouts e erros
- Não trava Claude Code durante execução

## TODO

- [ ] Implementar multi-start de máquinas (5 paralelas, 10s timeout)
- [ ] Cancelamento automático de máquinas não utilizadas
- [ ] Métricas de tempo de inicialização por host
- [ ] Cache de hosts "rápidos" para priorização futura
