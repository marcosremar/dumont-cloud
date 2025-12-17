# 📊 Página de Métricas de GPU - Documentação

## 🌐 Acesso

**URL:** http://54.37.225.188:8766/metrics

**Localização no Menu:** Dashboard → Machines → **Métricas** → Settings

## 📋 Funcionalidades

### 1. Filtros Inteligentes

- **GPU Selector**: Filtra por GPU específica ou mostra todas
  - Todas as GPUs
  - RTX 4090
  - RTX 4080

- **Time Range**: Seleciona período de análise
  - Última hora
  - Últimas 6 horas
  - Últimas 24 horas
  - Última semana

### 2. Status do Agente em Tempo Real

Mostra o status atual do agente de monitoramento:
- 🟢 **Rodando** ou 🔴 **Parado**
- Intervalo de monitoramento (30 minutos)
- Lista de GPUs sendo monitoradas

### 3. Cards de Resumo por GPU

Cada GPU monitorada tem um card com:

**Informações de Preço:**
- Preço médio atual (grande destaque)
- Preço mínimo encontrado
- Preço máximo encontrado

**Disponibilidade:**
- Total de ofertas disponíveis
- Total de GPUs disponíveis no mercado

**Tendência 24h:**
- Indicador visual (📈 subindo / 📉 caindo / ➡️ estável)
- Percentual de variação
- Cor: Verde (queda) / Vermelho (alta)

**Timestamp:**
- Data e hora da última atualização

### 4. Alertas Recentes (24h)

Lista de alertas automáticos quando há mudanças ≥10%:
- 💚 **Price Drop**: Preço caiu
- ⚠️ **Price Spike**: Preço subiu
- Mostra valores anterior e atual
- Percentual de mudança
- Timestamp do alerta

### 5. Histórico de Preços (Tabela)

Tabela completa com todos os registros do período selecionado:
- GPU
- Data/Hora
- Preço Médio
- Range (Mín - Máx)
- Quantidade de Ofertas
- Quantidade de GPUs

## 🎨 Design e UX

### Tema Visual
- **Dark Mode**: Tema escuro GitHub-like
- **Cores semânticas**:
  - Verde: Preços caindo (bom para comprar)
  - Vermelho: Preços subindo
  - Azul: Destaque de informações
  - Cinza: Informações secundárias

### Interatividade
- **Hover Effects**: Cards respondem ao mouse
- **Auto-refresh**: Atualiza dados a cada 60 segundos
- **Responsive**: Funciona em mobile, tablet e desktop
- **Loading States**: Mostra spinner durante carregamento

### Acessibilidade
- Fontes legíveis
- Alto contraste
- Labels descritivos
- Organização hierárquica clara

## 🔄 Atualização Automática

A página se atualiza automaticamente a cada **60 segundos**, buscando:
1. Status do agente
2. Resumo de preços atual
3. Histórico filtrado
4. Alertas recentes

Não precisa dar F5! Os dados são sempre atualizados em background.

## 📱 Responsividade

### Desktop (> 768px)
- Cards lado a lado (2 colunas)
- Tabela completa visível
- Todos os filtros no topo

### Tablet (768px - 1024px)
- Cards adaptam para 1-2 colunas
- Tabela com scroll horizontal

### Mobile (< 768px)
- Cards em coluna única
- Filtros empilhados
- Tabela simplificada com scroll

## 🎯 Casos de Uso

### 1. Encontrar Melhor Momento para Comprar
```
1. Acesse /metrics
2. Selecione a GPU desejada
3. Veja a tendência 24h:
   - Verde/Caindo? = Bom momento! 💚
   - Vermelho/Subindo? = Espere um pouco ⚠️
```

### 2. Comparar Preços entre GPUs
```
1. Selecione "Todas as GPUs"
2. Compare os preços médios nos cards
3. Veja qual tem mais ofertas disponíveis
```

### 3. Monitorar Alertas de Oportunidade
```
1. Olhe a seção "Alertas Recentes"
2. Procure por 💚 (quedas de preço)
3. Se houver queda ≥10%, considere comprar!
```

### 4. Analisar Tendências Históricas
```
1. Selecione "Última semana"
2. Veja a tabela de histórico
3. Identifique padrões de variação
```

## 🛠️ Tecnologias Utilizadas

### Frontend
- **React** 18
- **React Router** (navegação)
- **Hooks**: useState, useEffect
- **CSS** customizado (GitHub theme)

### Backend APIs
- `/api/price-monitor/status` - Status do agente
- `/api/price-monitor/summary` - Resumo com tendências
- `/api/price-monitor/history` - Histórico completo
- `/api/price-monitor/alerts` - Alertas de mudança

### Design System
- Variáveis CSS customizadas
- Grid responsivo
- Flexbox layouts
- Transições suaves

## 📊 Dados Exibidos

### Por GPU Card:
```javascript
{
  gpu_name: "RTX 4090",
  current: {
    avg_price: 0.3361,      // Preço médio ($/hora)
    min_price: 0.1489,      // Mínimo
    max_price: 0.6022,      // Máximo
    median_price: 0.3356,   // Mediana
    total_offers: 64,       // Ofertas
    available_gpus: 64,     // GPUs
    timestamp: "2025-12-16T19:14:03"
  },
  trend_24h: {
    direction: "up",        // up / down / stable
    change_percent: 1.98,   // Variação %
    lowest_avg: 0.3296,     // Menor média do período
    highest_avg: 0.3361,    // Maior média do período
    period_avg: 0.3326      // Média do período
  }
}
```

## 🚀 Melhorias Futuras

- [ ] Gráficos de linha (Chart.js)
- [ ] Exportar dados em CSV/Excel
- [ ] Notificações push quando preço cair
- [ ] Previsão de preços com ML
- [ ] Comparação com preços históricos
- [ ] Filtro por região geográfica
- [ ] Dashboard customizável

## ⚡ Performance

- **Caching**: Dados cacheados por 60s
- **Lazy Loading**: Componentes carregam sob demanda
- **Otimização**: Bundle minificado e comprimido
- **API Calls**: Apenas quando necessário

## 🎉 Pronto para Uso!

A página já está **FUNCIONANDO** e pode ser acessada imediatamente em:

**http://54.37.225.188:8766/metrics**

Todos os dados são reais e atualizados a cada 30 minutos pelo agente de monitoramento!
