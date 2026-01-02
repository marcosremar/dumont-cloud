# Relatório de Teste - Wizard GPU Reserva

## Data do Teste
2 de Janeiro de 2026

## Objetivo
Testar o fluxo completo do wizard de reserva de GPU desde a seleção de região até o provisionamento.

## Ambiente
- URL: http://localhost:4898/demo-app
- Browser: Chromium (Playwright)
- Modo: Demo

## Resultados do Teste

### ✅ Steps que Funcionaram Corretamente

1. **STEP 1**: Navegação para /demo-app → ✅ OK
2. **STEP 2**: Snapshot inicial → ✅ OK
3. **STEP 3**: Clicar no botão "EUA" → ✅ OK
4. **STEP 4**: Badge "EUA" aparece após seleção → ✅ OK (confirmado em screenshot)
5. **STEP 5**: Botão "Próximo" fica habilitado → ✅ OK

### ❌ Problema Encontrado: Perda de Estado ao Clicar em "Próximo"

**Descrição do Bug**:
Quando o usuário clica no botão "Próximo" após selecionar uma região, a seleção **desaparece** e o wizard **não avança** para o Step 2.

**Evidências**:

1. **Screenshot wizard-step-02-eua-selecionado.png**:
   - Badge "EUA X" visível
   - Mapa mostra países da região em verde (US, CA, MX)
   - Botão "Próximo" habilitado (verde)
   - **Estado correto**: selectedLocation = { codes: ['US', 'CA', 'MX'], name: 'EUA', isRegion: true }

2. **Screenshot wizard-step-03-hardware.png** (após clicar em "Próximo"):
   - Badge "EUA" **DESAPARECEU**
   - Ainda no Step 1/4 "Região"
   - Botões de região novamente visíveis
   - **Estado incorreto**: selectedLocation = null (perdeu o valor)

**Comportamento Esperado**:
- Ao clicar em "Próximo", deve avançar para Step 2/4 "Hardware"
- Deve mostrar botões de caso de uso: "Desenvolver", "Treinar modelo", "Produção"
- Deve manter a região selecionada (EUA)

**Comportamento Atual**:
- Permanece no Step 1/4 "Região"
- Perde a seleção de região
- Não avança para o próximo step

## Análise Técnica

### Código Relevante

**WizardForm.jsx** (linha 391-397):
```jsx
const isStepDataComplete = (stepId) => {
  if (stepId === 1) return !!selectedLocation;
  if (stepId === 2) return !!selectedTier;
  if (stepId === 3) return !!failoverStrategy;
  if (stepId === 4) return !!provisioningWinner;
  return false;
};
```

**WizardForm.jsx** (linha 420-429):
```jsx
const handleNext = () => {
  if (currentStep < steps.length && isStepComplete(currentStep)) {
    // Se está no step 3 e vai para o step 4, iniciar provisioning
    if (currentStep === 3) {
      handleStartProvisioning();
    } else {
      setCurrentStep(currentStep + 1);
    }
  }
};
```

### Hipóteses sobre a Causa

1. **Hipótese 1**: O estado selectedLocation está sendo resetado durante a transição de steps
2. **Hipótese 2**: O componente está fazendo unmount/remount durante a navegação
3. **Hipótese 3**: O clique em "Próximo" está disparando eventos múltiplos

## Próximos Passos

### 1. Investigar o Bug no Frontend
- Verificar logs do console do browser
- Adicionar console.log no handleNext e handleRegionSelect
- Verificar se selectedLocation está sendo mantido no Dashboard.jsx

## Screenshots Salvos

1. wizard-step-01-inicial.png - Página inicial do wizard
2. wizard-step-02-eua-selecionado.png - EUA selecionado com badge visível
3. wizard-step-03-hardware.png - Após clicar Próximo (BUG: seleção perdida)

## Conclusão

O teste identificou um **BUG CRÍTICO** no wizard que impede o usuário de avançar do Step 1 (Região) para o Step 2 (Hardware). A seleção de região é perdida ao clicar em "Próximo", fazendo com que o wizard fique travado no primeiro step.

**Prioridade**: ALTA
**Impacto**: Bloqueia completamente o fluxo de criação de instâncias GPU
