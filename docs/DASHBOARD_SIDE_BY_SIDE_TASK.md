# 📋 Tarefa: Exibir Modo Avançado ao Lado do Wizard

## 🎯 Objetivo
No Dashboard, existem 2 modos de busca:
1. **Wizard** (visível) - Modo simplificado com mapa e seleção visual
2. **Advanced** (oculto em tab) - Filtros avançados detalhados

**Meta:** Exibir os dois side-by-side, não em tabs

## 📐 Estrutura Atual

```jsx
// Botões de alternância (linhas ~1690-1712)
<button onClick={() => setMode('wizard')}>AI</button>
<button onClick={() => setMode('advanced')}>Avançado</button>

/dash {mode === 'wizard'  \u0026\u0026 !showResults \u0026\u0026 (...)}  // Wizard View
{mode === 'advanced' \u0026\u0026 !showResults \u0026\u0026 (...)}  // Advanced View  
```

## ✅ Solução

Transformar em um layout de 2 colunas:
- **Coluna Esquerda (60%):** Wizard (mapa + seleção visual)
- **Coluna Direita (40%):** Advanced (filtros avançados colapsáveis)

### Mudanças Necessárias

1. Remover botões de alternância de modo
2. Criar grid de 2 colunas
3. Wizard na esquerda (sempre visível)
4. Advanced na direita com accordion/collapse
5. Manter AI Advisor integrado

## 🎨 Layout Proposto

```
+----------------------------------------+
|  [Wizard Mode]    |  [Advanced Mode]  |
|  - Mapa          |  - GPU Filters     |
|  - GPU Selector  |  - CPU/Memory      |
|  - AI Advisor    |  - Performance     |
|  - Tiers         |  - Network         |
|                  |  - Price           |
|                  |  [Search Button]   |
+----------------------------------------+
```

## 🔄 Implementação
Arquivo: `/web/src/pages/Dashboard.jsx`
Linhas a modificar: ~1680-1850

