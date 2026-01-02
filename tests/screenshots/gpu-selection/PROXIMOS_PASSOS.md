# Próximos Passos - Investigação do Wizard GPU

Este guia prático te ajuda a investigar e corrigir os problemas identificados no teste visual.

---

## 1️⃣ Teste Manual (5 minutos)

### Abrir wizard e inspecionar

```bash
# 1. Abrir o app em modo DEMO
open "http://localhost:4894/demo-app"

# 2. No browser:
# - Abrir DevTools (F12 ou Cmd+Opt+I)
# - Navegar: Região → Propósito → GPU
# - No passo de GPU, clicar em "Inspect Element" em um card
# - Copiar HTML do card de GPU
```

### O que procurar:
- [ ] O card tem nome de GPU (ex: "RTX 4090")?
- [ ] O card tem botão "Selecionar" ou similar?
- [ ] Existem data-attributes (ex: `data-gpu-offer`)?
- [ ] Qual é a classe CSS do card?
- [ ] Como é a estrutura HTML?

---

## 2️⃣ Rodar Teste em Modo Debug (10 minutos)

### Teste interativo com Playwright Inspector

```bash
cd /Users/marcos/CascadeProjects/dumontcloud/tests

# Rodar em modo debug (abre inspetor visual)
npx playwright test wizard-gpu-demo-visual.spec.js --debug --project=chromium
```

**Como usar:**
1. Teste pausa em cada `await`
2. Você pode clicar manualmente na página
3. Console mostra seletores disponíveis
4. Explorar o DOM em tempo real

### Pausar em passo específico

Adicionar no teste:
```javascript
// Pausar no passo de GPU para investigar
await page.pause(); // Abre inspetor
```

---

## 3️⃣ Capturar HTML do Passo de GPU

### Método 1: Via Browser

```javascript
// No console do DevTools (F12):
console.log(document.querySelector('[class*="wizard"]').innerHTML);

// Ou copiar elemento específico:
copy(document.querySelector('[class*="gpu-card"]'));
```

### Método 2: Via Playwright

```bash
# Rodar teste de inspeção (se completar)
npx playwright test wizard-gpu-inspect-dom.spec.js --project=chromium

# Ver arquivos gerados:
ls -lh screenshots/gpu-selection/dom-inspection*
```

---

## 4️⃣ Verificar Dados Mockados

### Ver o que a API retorna

```bash
# Testar endpoint de ofertas GPU
curl -X GET "http://localhost:8766/api/v1/advisor/offers?demo=true" \
  -H "Content-Type: application/json" | jq

# Ou com query params específicos:
curl "http://localhost:8766/api/v1/advisor/offers?region=US&purpose=develop&demo=true" | jq
```

### O que validar:
- [ ] API retorna array de ofertas?
- [ ] Cada oferta tem `gpu_name`?
- [ ] Cada oferta tem `price_hour`?
- [ ] Cada oferta tem `id`?

---

## 5️⃣ Adicionar Data Attributes no Componente

### Arquivo a editar:
`/Users/marcos/CascadeProjects/dumontcloud/web/src/components/dashboard/WizardForm.jsx`

### Exemplo de correção:

```jsx
// ANTES (difícil de testar)
<div className="gpu-card">
  <h3>{offer.gpu_name}</h3>
  <p>${offer.price_hour}/hora</p>
  <button onClick={() => selectGpu(offer)}>
    Selecionar
  </button>
</div>

// DEPOIS (fácil de testar)
<div
  className="gpu-card"
  data-gpu-offer
  data-offer-id={offer.id}
  data-gpu-name={offer.gpu_name}
>
  <h3 data-label="gpu-name">{offer.gpu_name}</h3>
  <p data-label="price">${offer.price_hour}/hora</p>
  <button
    onClick={() => selectGpu(offer)}
    data-action="select-gpu"
    data-offer-id={offer.id}
  >
    Selecionar
  </button>
</div>
```

### Vantagens:
- Testes usam `page.locator('[data-gpu-offer]')`
- Independente de classes CSS (que mudam)
- Explícito e autodocumentado

---

## 6️⃣ Atualizar Teste com Seletores Corretos

### Depois de descobrir a estrutura real:

```javascript
// Exemplo baseado na estrutura real descoberta
test('Selecionar GPU no wizard', async ({ page }) => {
  // ... navegar até passo de GPU ...

  // Usar seletores descobertos na inspeção:
  const gpuCards = page.locator('[data-gpu-offer]'); // Se existir
  // OU
  const gpuCards = page.locator('.gpu-card-real-class'); // Classe real

  // Pegar primeira GPU
  const firstGpu = gpuCards.first();

  // Verificar que tem nome
  await expect(firstGpu.locator('[data-label="gpu-name"]')).toContainText(/RTX|A100|H100/);

  // Clicar em selecionar
  await firstGpu.locator('[data-action="select-gpu"]').click();

  // Verificar selecionado
  await expect(firstGpu).toHaveClass(/selected|active/);
});
```

---

## 7️⃣ Comandos Úteis para Debug

### Ver screenshots gerados:

```bash
# Abrir pasta de screenshots
open /Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/gpu-selection/

# Ver último screenshot
open screenshots/gpu-selection/10-wizard-completo.png
```

### Ver logs do teste:

```bash
# Log completo
cat screenshots/gpu-selection/teste-visual-log.txt

# Relatório detalhado
open screenshots/gpu-selection/RELATORIO_TESTE_VISUAL.md
```

### Rodar teste específico:

```bash
# Teste visual completo
npx playwright test wizard-gpu-demo-visual.spec.js --project=chromium

# Teste de inspeção
npx playwright test wizard-gpu-inspect-dom.spec.js --project=chromium

# Com headed mode (ver browser)
npx playwright test wizard-gpu-demo-visual.spec.js --headed --project=chromium
```

---

## 8️⃣ Checklist de Validação

### Antes de marcar como "resolvido":

- [ ] Teste manual funciona (consegue selecionar GPU)
- [ ] API retorna GPUs mockadas corretamente
- [ ] Cards de GPU têm data-attributes
- [ ] Teste automatizado consegue localizar cards
- [ ] Teste automatizado consegue clicar em "Selecionar"
- [ ] Teste automatizado consegue verificar seleção
- [ ] Teste automatizado consegue avançar para próximo passo
- [ ] 10/10 screenshots mostram fluxo completo

---

## 9️⃣ Perguntas para Responder

Após investigação manual, documente:

1. **Quantos passos o wizard tem no total?**
   - [ ] 3 passos
   - [ ] 4 passos
   - [ ] Outro: ____

2. **Qual é o texto do botão final?**
   - [ ] "Próximo"
   - [ ] "Criar"
   - [ ] "Provisionar"
   - [ ] Outro: ____

3. **Estrutura do card de GPU:**
   ```html
   <!-- Colar HTML real aqui -->
   ```

4. **Seletor que funciona para cards:**
   ```javascript
   // Ex: '[data-gpu-offer]'
   // Ex: '.gpu-offer-card'
   ```

5. **Como identificar GPU selecionada?**
   - [ ] Classe CSS `selected`
   - [ ] Classe CSS `active`
   - [ ] Attribute `aria-selected="true"`
   - [ ] Outro: ____

---

## 🎯 Objetivo Final

Ter um teste que:
1. Navega por TODOS os passos do wizard
2. Seleciona uma GPU real
3. Verifica seleção visualmente
4. Avança até o final (botão "Criar"/"Provisionar")
5. Captura 15+ screenshots do fluxo completo

### Resultado esperado:
```
✅ 15 screenshots capturados
✅ GPU "RTX 4090" selecionada
✅ Botão "Criar" habilitado
✅ Fluxo completo validado
```

---

## 📞 Onde Pedir Ajuda

Se encontrar problemas:

1. **Logs do backend:**
   ```bash
   # Ver se há erros ao carregar GPUs
   tail -f /var/log/dumont/backend.log | grep -i gpu
   ```

2. **Console do browser:**
   - Abrir DevTools → Console
   - Procurar por erros em vermelho
   - Verificar chamadas de API (Network tab)

3. **Playwright trace:**
   ```bash
   npx playwright test --trace on
   npx playwright show-trace trace.zip
   ```

---

## ✅ Quando Estiver Resolvido

Atualizar este arquivo com:
- [x] Seletores corretos encontrados
- [x] Data-attributes adicionados
- [x] Teste automatizado funcionando
- [x] Screenshots completos gerados

E criar PR com:
- Correções no `WizardForm.jsx`
- Teste atualizado
- Screenshots de evidência
- Documentação do fluxo

---

**Bom trabalho! 🚀**

Qualquer dúvida, consulte os relatórios gerados:
- `SUMARIO_EXECUTIVO.md` - Visão geral
- `RELATORIO_TESTE_VISUAL.md` - Detalhes técnicos
- `CONCLUSAO_TESTE_GPU_WIZARD.md` - Problemas e soluções
