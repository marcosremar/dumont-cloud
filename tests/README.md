# 🚀 VibeCoding Test Suite - Dumont Cloud

## Estrutura de Testes (Pirâmide VibeCoding)

```
                    🎨 Vibe Tests (10%)
                   "Está bonito?"

              ┌─────────────────────────┐
              │  🤖 E2E User Journeys    │  20%
              │  (Ações REAIS de usuário)│
              └─────────────────────────┘

         ┌───────────────────────────────────┐
         │  🎯 API Contract Tests            │  30%
         │  (Pydantic Schema Validation)     │
         └───────────────────────────────────┘

    ┌─────────────────────────────────────────┐
    │  ⚡ Smoke Tests (Always Run)            │  40%
    │  Health + Auth + Demo Mode              │
    │  Tempo: <10s                            │
    └─────────────────────────────────────────┘
```

---

## 📁 Estrutura de Diretórios

```
tests/
├── smoke/                          ⚡ 40% - CAMADA 1
│   ├── conftest.py
│   └── test_smoke.py              # 9 testes essenciais
│
├── contract/                       🎯 30% - CAMADA 2
│   ├── conftest.py
│   └── test_api_contracts.py       # 9 testes de schema
│
├── e2e-journeys/                   🤖 20% - CAMADA 3
│   ├── auth.setup.js              # Setup de autenticação
│   └── REAL-user-actions.spec.js  # 9 testes de ações REAIS
│
├── vibe/                           🎨 10% - CAMADA 4
│   └── test_vibe.py               # 15 testes UX
│
└── browser-use/                    🤖 Bonus - IA Visual
    └── (opcional - browser-use agent)
```

---

## 🤖 E2E User Journeys - Conceito

### O que são E2E User Journeys?

São testes que **simulam um usuário REAL** fazendo **ações REAIS** e **verificam RESULTADOS**.

### ❌ Teste SUPERFICIAL (errado)
```javascript
// Passa mesmo sem funcionar!
if (await button.isVisible().catch(() => false)) {
  console.log('✅ OK');
} else {
  console.log('⚠️ Não encontrado');  // PASSA MESMO ASSIM!
}
```

### ✅ Teste REALISTA (correto)
```javascript
// FALHA se não funcionar
test('Usuário consegue INICIAR uma máquina', async ({ page }) => {
  // 1. Encontrar máquina PARADA
  const offlineMachine = page.locator('[class*="rounded-lg"]').filter({
    has: page.locator('text="Offline"')
  }).first();

  // 2. Clicar em INICIAR
  await offlineMachine.locator('button:has-text("Iniciar")').click();

  // 3. VERIFICAR toast apareceu
  await expect(page.locator('text=/Iniciando/')).toBeVisible();

  // 4. VERIFICAR que status mudou para Online
  await expect(page.locator('text="Online"')).toBeVisible({ timeout: 5000 });
});
```

### Diferenças Chave

| Aspecto | Teste Superficial | Teste Realista |
|---------|-------------------|----------------|
| Verifica clique? | ✅ | ✅ |
| Verifica resultado? | ❌ | ✅ |
| Falha se quebrar? | ❌ | ✅ |
| Simula usuário? | ❌ | ✅ |

---

## 🎯 Testes E2E Atuais (9 testes)

### Ações de Usuário
| Teste | O que verifica |
|-------|----------------|
| Ver máquinas | 5 máquinas carregam com dados |
| **INICIAR máquina** | Clica → Toast → Status "Online" |
| **PAUSAR máquina** | Clica → Modal → Toast → Pausa |
| Navegar menu | Dashboard → Machines → Settings |
| Ver métricas | GPU%, Temperatura, Custo/hora |
| Settings | Seções API e CPU Standby |

### Fluxos Completos
| Teste | Passos |
|-------|--------|
| Fluxo Iniciar | Dashboard → Machines → Iniciar → Verifica |
| Fluxo Economia | Dashboard → Cards de economia visíveis |

---

## 🏃 Como Rodar os Testes

### Rodar TUDO (Recomendado)
```bash
# Todas as 4 camadas
pytest tests/smoke tests/contract tests/vibe -v
npx playwright test tests/e2e-journeys/

# Resultado esperado: ~42 testes passando em ~1 minuto
```

### Por Camada

#### ⚡ Camada 1: Smoke Tests (10s)
```bash
pytest tests/smoke/ -v --timeout=10
# 9 testes, esperado: 100% pass rate
```

#### 🎯 Camada 2: Contract Tests (2min)
```bash
pytest tests/contract/ -v
# 9 testes, esperado: 100% pass rate
```

#### 🤖 Camada 3: E2E Journeys (30s)
```bash
npx playwright test tests/e2e-journeys/
# 9 testes REAIS, esperado: 100% pass rate
```

#### 🎨 Camada 4: Vibe Tests
```bash
pytest tests/vibe/ -v --timeout=30
# 15 testes UX & visual validation
```

---

## ✅ Status Atual (Dezembro 2024)

| Camada | Testes | Status | Tempo |
|--------|--------|--------|-------|
| Smoke | 9/9 | ✅ 100% | ~5s |
| Contract | 9/9 | ✅ 100% | ~2s |
| E2E Journeys | 9/9 | ✅ 100% | ~27s |
| Vibe Tests | 15/15 | ✅ 100% | ~4s |
| **TOTAL** | **42/42** | **✅ 100%** | **~40s** |

---

## 🔧 Arquitetura dos E2E Journeys

### Autenticação Compartilhada
```javascript
// auth.setup.js - Roda UMA vez antes de todos os testes
test('authenticate', async ({ page }) => {
  await page.goto('/login');
  await page.fill('input[type="email"]', 'test@test.com');
  await page.fill('input[type="password"]', 'test123');
  await page.click('button[type="submit"]');

  // Salva estado de autenticação
  await page.context().storageState({ path: 'tests/.auth/user.json' });
});
```

### Seletores Robustos
```javascript
// ❌ Frágil - quebra se mudar classe
page.locator('.btn-primary-v2')

// ✅ Robusto - baseado em comportamento
page.locator('button:has-text("Iniciar")')

// ✅ Robusto - excluir elementos invisíveis
page.locator('a:not(.mobile-menu-link):has-text("Machines")')
```

### Verificações de Estado
```javascript
// ❌ Só verifica se existe
await expect(button).toBeVisible();

// ✅ Verifica mudança de estado
await button.click();
await expect(page.locator('text="Online"')).toBeVisible();
```

---

## 💡 Princípios VibeCoding para E2E

1. **Teste a Ação, Não o Elemento**
   - ✅ "Máquina inicia quando clico em Iniciar"
   - ❌ "Botão com classe X está visível"

2. **Verifique Resultados, Não Cliques**
   - ✅ Após clicar, verificar que status mudou
   - ❌ Só verificar que clicou

3. **Falhe se Quebrar**
   - ✅ `await expect(element).toBeVisible()`
   - ❌ `if (await element.isVisible().catch(() => false))`

4. **Simule Usuários Reais**
   - ✅ Fluxos completos: Login → Ação → Verificação
   - ❌ Testes isolados sem contexto

5. **Logs Úteis**
   ```javascript
   console.log('✅ Máquina RTX 3090 iniciada com sucesso!');
   // Ajuda a debugar quando algo falha
   ```

---

## 📚 Referências

- **Playwright Docs**: https://playwright.dev/docs/test-assertions
- **VibeCoding Strategy**: `Live-Doc/content/Engineering/VibeCoding_Testing_Strategy.md`
- **Playwright Config**: `playwright.config.js`
- **Pytest Config**: `pytest.ini`

---

**Última atualização**: Dezembro 2024
**Status**: ✅ Testes E2E Realistas implementados
**Cobertura**: Ações críticas (Iniciar, Pausar, Navegar, Métricas)
