---
description: Capturar screenshots de todas as telas e analisar layout
---

# Screenshot e Análise de Layout

Este workflow captura screenshots de todas as páginas da aplicação e analisa problemas de layout.

## Pré-requisitos
- Node.js instalado
- Servidor de desenvolvimento rodando (porta 5173)

## Passos

### 1. Verificar se o servidor está rodando
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:5173
```
Se retornar "000", inicie o servidor:
```bash
cd /home/marcos/dumontcloud/web && npm run dev
```

### 2. Executar captura em background
// turbo
```bash
cd /home/marcos/dumontcloud/scripts/screenshots && ./run-in-background.sh
```

### 3. Verificar status da captura
// turbo
```bash
cd /home/marcos/dumontcloud/scripts/screenshots && ./run-in-background.sh --status
```

### 4. Ver logs em tempo real (opcional)
```bash
cd /home/marcos/dumontcloud/scripts/screenshots && ./run-in-background.sh --logs
```

### 5. Executar análise de código
// turbo
```bash
cd /home/marcos/dumontcloud/scripts/screenshots && node analyze-layout.js
```

### 6. Ver relatório
Os resultados estarão em:
- Screenshots: `/home/marcos/dumontcloud/artifacts/screenshots/*.png`
- Relatório JSON: `/home/marcos/dumontcloud/artifacts/screenshots/layout-analysis.json`
- Relatório MD: `/home/marcos/dumontcloud/artifacts/screenshots/LAYOUT_ANALYSIS_REPORT.md`

## Recuperação de Falhas

Se a captura for interrompida, use:
```bash
cd /home/marcos/dumontcloud/scripts/screenshots && ./run-in-background.sh --resume
```

Para parar uma captura em andamento:
```bash
cd /home/marcos/dumontcloud/scripts/screenshots && ./run-in-background.sh --stop
```

## Arquivos do Script
- `capture-all-screens.js` - Script principal de captura (Playwright)
- `analyze-layout.js` - Script de análise de código
- `run-in-background.sh` - Wrapper para execução em background
- `screenshot-state.json` - Estado para recuperação
