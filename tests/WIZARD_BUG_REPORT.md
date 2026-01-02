# Wizard Bug Report - Estado não persiste entre cliques

## Problema Identificado

O wizard não avança do Step 1 (Região) para o Step 2 (Hardware) mesmo quando o usuário seleciona uma região (EUA, Europa, etc).

## Sintomas

1. Usuário clica em "EUA" → badge de seleção aparece momentaneamente
2. Botão "Próximo" fica habilitado por um momento
3. **Estado é resetado** → badge desaparece
4. Botão "Próximo" volta a ficar disabled
5. Usuário não consegue avançar para o próximo step

## Evidências dos Testes

### Console Logs Capturados

```
[BROWSER LOG]: 🔍 handleRegionSelect called: eua
[BROWSER LOG]: 🔍 regionData: {codes: Array(3), name: EUA, isRegion: true}
[BROWSER LOG]: ✅ selectedLocation set to: {codes: Array(3), name: EUA, isRegion: true}
[BROWSER LOG]: 🔍 isStepDataComplete(1): true {selectedLocation: Object, selectedTier: null, failoverStrategy: snapshot_only}
```

**Mas depois:**

```
Selected location visible: false
--- Clicking "Próximo" button ---
[BROWSER LOG]: 🔍 isStepDataComplete(1): false {selectedLocation: null, selectedTier: null, failoverStrategy: snapshot_only}
Next button enabled: false
```

### Error Context (DOM Snapshot)

```yaml
- button "EUA" [ref=e210] [cursor=pointer]:  # Botão presente
- button "Próximo" [disabled] [ref=e420]:    # DISABLED
```

**Observação crítica:** Não há badge de seleção visível no DOM (não aparece "EUA" ou "Estados Unidos" selecionado).

## Causa Raiz

O componente `Dashboard.jsx` está sendo **remontado** ou há um **re-render não intencional** que reseta o estado `selectedLocation` para `null`.

### Evidências de Re-Render

1. **Múltiplos inicializadores do i18next:**
   ```
   [BROWSER LOG]: i18next::backendConnector: loaded namespace...
   [BROWSER LOG]: i18next: languageChanged en
   [BROWSER LOG]: i18next: initialized...
   ```

2. **Erros de API 401:**
   ```
   [BROWSER ERROR]: Failed to load resource: the server responded with a status of 401 (Unauthorized)
   ```

3. **React DevTools aparece múltiplas vezes:**
   ```
   [BROWSER INFO]: %cDownload the React DevTools...
   ```

## Possíveis Causas

### 1. Erros 401 causando re-render
Os erros 401 podem estar disparando algum interceptor que força um re-render ou navigation.

### 2. useEffect com dependências incorretas
Algum `useEffect` pode ter dependências que causam re-renders desnecessários.

### 3. Estado não persistido corretamente
O estado `selectedLocation` pode estar sendo gerenciado incorretamente, causando perda de dados.

### 4. Problema de WebSocket (Vite HMR)
```
[BROWSER ERROR]: WebSocket connection to 'ws://localhost:4892/?token=...' failed
[BROWSER LOG]: [vite] server connection lost. Polling for restart...
```

O Vite está tentando conectar a um WebSocket na porta 4892 (HMR - Hot Module Replacement) mas falhando, o que pode estar causando reloads.

## Arquivos Afetados

- `/web/src/pages/Dashboard.jsx` - Linha 456 (definição de `selectedLocation`)
- `/web/src/pages/Dashboard.jsx` - Linhas 487-498 (`handleRegionSelect`)
- `/web/src/components/dashboard/WizardForm.jsx` - Linhas 391-401 (`isStepDataComplete`)

## Reprodução

```bash
# 1. Iniciar frontend na porta 4898
cd web && npm run dev

# 2. Rodar teste de debug
npx playwright test wizard-simple.spec.js --project=wizard-debug

# Resultado esperado: Teste falha com "Next button is disabled"
```

### Reprodução Manual

1. Abrir `http://localhost:4898/demo-app`
2. Executar `localStorage.setItem('demo_mode', 'true')` no console
3. Clicar em "EUA"
4. **Observar:** Badge aparece e depois desaparece
5. Botão "Próximo" permanece desabilitado

## Próximos Passos (Sugestões de Fix)

### Fix 1: Prevenir Re-Renders Desnecessários

```jsx
// Dashboard.jsx
const [selectedLocation, setSelectedLocation] = useState(() => {
  // Try to restore from sessionStorage
  const saved = sessionStorage.getItem('wizard_selectedLocation');
  return saved ? JSON.parse(saved) : null;
});

// Save to sessionStorage when changed
useEffect(() => {
  if (selectedLocation) {
    sessionStorage.setItem('wizard_selectedLocation', JSON.stringify(selectedLocation));
  }
}, [selectedLocation]);
```

### Fix 2: Debugar Erros 401

Verificar se há algum interceptor de API que força re-render em erros 401.

```bash
# Procurar por interceptors
grep -r "interceptor\|401\|Unauthorized" web/src/utils/
```

### Fix 3: Desabilitar Vite HMR para Testes

```js
// vite.config.js (apenas para debug)
server: {
  hmr: false, // Desabilitar HMR temporariamente
}
```

### Fix 4: Adicionar Debug Logs

```jsx
// WizardForm.jsx - linha 391
const isStepDataComplete = (stepId) => {
  const result = (() => {
    if (stepId === 1) return !!selectedLocation;
    if (stepId === 2) return !!selectedTier;
    if (stepId === 3) return !!failoverStrategy;
    if (stepId === 4) return !!provisioningWinner;
    return false;
  })();

  // ADD THIS:
  if (stepId === 1 && !result && selectedLocation === null) {
    console.error('❌ CRITICAL: selectedLocation is null when checking step 1 completion!');
    console.trace('Stack trace:');
  }

  console.log(`🔍 isStepDataComplete(${stepId}):`, result, { selectedLocation, selectedTier, failoverStrategy });
  return result;
};
```

## Conclusão

O wizard tem um bug crítico onde o estado `selectedLocation` é perdido após ser setado, provavelmente devido a:
1. Re-renders causados por erros 401
2. Problemas com Vite HMR WebSocket
3. Possível navigation/redirect não intencional

**Recomendação:** Persistir o estado do wizard em `sessionStorage` como workaround imediato e investigar os erros 401 e WebSocket para fix definitivo.
