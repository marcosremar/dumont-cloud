# Chat Arena - Error Prevention and Improvements

## Summary

This document describes the error handling improvements made to the Chat Arena feature to prevent common failures and provide better user experience.

## Error Scenarios and Preventions

### 1. Network Timeout

**Problem:** Ollama API calls could hang indefinitely if the server doesn't respond.

**Solution:** Implemented `fetchWithTimeout()` helper with:
- Configurable timeout (default 60s for health check, 120s for inference)
- AbortController for request cancellation
- Automatic retry on timeout (up to 2 retries)

```javascript
const fetchWithTimeout = async (url, options = {}, timeoutMs = 60000, retries = 2) => {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs)
    // ... with retry logic
}
```

### 2. Model Offline/Unavailable

**Problem:** User could select a model that went offline after initial fetch.

**Solution:** Added `checkModelHealth()` that verifies model availability before sending messages:
- Checks Ollama `/api/tags` endpoint with 5s timeout
- Returns `{ healthy: false, error: 'reason' }` if unavailable
- Lists installed models for selection

### 3. CORS Errors

**Problem:** Cross-origin requests to Ollama instances may fail with unclear errors.

**Solution:** Enhanced error detection in fetchWithTimeout:
```javascript
if (error.message.includes('CORS') || error.message.includes('Failed to fetch')) {
    throw new Error('Erro de conexão: verifique se o modelo está online e acessível')
}
```

### 4. No Models Installed

**Problem:** Ollama server running but no models pulled yet.

**Solution:** Health check returns specific error:
```javascript
if (!data.models || data.models.length === 0) {
    return { healthy: false, error: 'Nenhum modelo instalado', models: [] }
}
```

### 5. Invalid JSON Response

**Problem:** Corrupted or unexpected response format could crash the UI.

**Solution:** Wrapped JSON parsing with try-catch:
```javascript
let data
try {
    data = await response.json()
} catch (e) {
    throw new Error('Resposta inválida do modelo')
}
```

### 6. Empty Model Response

**Problem:** Model might return empty content without error status.

**Solution:** Validate response content:
```javascript
if (!content || content === 'Sem resposta') {
    throw new Error('Modelo retornou resposta vazia')
}
```

### 7. HTTP Error Responses

**Problem:** Non-200 responses weren't showing useful error messages.

**Solution:** Extract and display actual error text:
```javascript
if (!response.ok) {
    const errorText = await response.text().catch(() => response.statusText)
    throw new Error(`Erro ${response.status}: ${errorText}`)
}
```

## New Templates Added

Added pre-configured Ollama templates for easy deployment:

| ID | Name | Model | VRAM Required |
|----|------|-------|---------------|
| 5 | Ollama | Base (no model) | 4GB |
| 6 | Ollama + Llama 3.2 3B | llama3.2:3b | 4-6GB |
| 7 | Ollama + Qwen 2.5 3B | qwen2.5:3b | 4-6GB |

## Error Messages (Portuguese)

All error messages are in Portuguese for consistent UX:
- "URL do modelo não disponível"
- "Modelo offline"
- "Nenhum modelo instalado"
- "Erro de conexão: verifique se o modelo está online e acessível"
- "Timeout: servidor demorou mais de Xs"
- "Resposta inválida do modelo"
- "Modelo retornou resposta vazia"
- "Erro {status}: {details}"

## Playwright Tests Created

Test file: `tests/chat-arena-interactive.spec.js`

Tested features:
- Model selector dropdown
- Multiple model selection
- System prompt modal
- Message sending
- Demo response verification
- Metrics display (tokens/s, response time)
- Export to Markdown
- Export to JSON
- Clear conversations

## Future Improvements

1. **Streaming Responses** - Show tokens as they arrive for better UX
2. **Model Status Indicator** - Real-time health check in model selector
3. **Connection Recovery** - Auto-reconnect when model comes back online
4. **Request Queue** - Handle high-frequency requests gracefully
5. **Rate Limiting Protection** - Detect and handle Ollama rate limits
