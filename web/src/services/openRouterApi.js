/**
 * OpenRouter API Service
 * Handles communication with OpenRouter for LLM inference
 */

const OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'

/**
 * Get OpenRouter API key from localStorage or environment
 */
export function getOpenRouterApiKey() {
  // Check localStorage first (user-provided key)
  const storedKey = localStorage.getItem('openrouter_api_key')
  if (storedKey) return storedKey

  // Fallback to environment variable (for demo/development)
  return import.meta.env.VITE_OPENROUTER_API_KEY || null
}

/**
 * Set OpenRouter API key in localStorage
 */
export function setOpenRouterApiKey(apiKey) {
  if (apiKey) {
    localStorage.setItem('openrouter_api_key', apiKey)
  } else {
    localStorage.removeItem('openrouter_api_key')
  }
}

/**
 * Check if OpenRouter API key is configured
 */
export function hasOpenRouterApiKey() {
  return !!getOpenRouterApiKey()
}

/**
 * Send a chat completion request to OpenRouter
 * @param {Object} params - Request parameters
 * @param {string} params.model - Model ID (e.g., 'openai/gpt-4o-mini')
 * @param {Array} params.messages - Chat messages array
 * @param {number} params.temperature - Temperature (0-2)
 * @param {number} params.max_tokens - Max tokens to generate
 * @param {number} params.top_p - Top P value
 * @param {string} params.responseFormat - 'text' or 'json'
 * @param {Array} params.tools - Tool definitions for function calling
 * @param {Array} params.functions - Function definitions
 * @param {Function} params.onStream - Callback for streaming responses
 * @returns {Promise<Object>} - Chat completion response
 */
export async function chatCompletion({
  model,
  messages,
  temperature = 0.7,
  max_tokens = 2048,
  top_p = 1,
  responseFormat = 'text',
  tools = [],
  functions = [],
  onStream = null
}) {
  const apiKey = getOpenRouterApiKey()

  if (!apiKey) {
    throw new Error('OpenRouter API key not configured. Please add your API key in Settings.')
  }

  const requestBody = {
    model,
    messages,
    temperature,
    max_tokens,
    top_p,
    stream: !!onStream
  }

  // Add response format if JSON
  if (responseFormat === 'json') {
    requestBody.response_format = { type: 'json_object' }
  }

  // Add tools if specified (OpenRouter format)
  if (tools.length > 0) {
    requestBody.tools = tools.map(toolId => {
      switch (toolId) {
        case 'code':
          return {
            type: 'function',
            function: {
              name: 'execute_code',
              description: 'Execute Python code immediately. Do NOT explain - just run the code. Always use print() for output. Numpy is available.',
              parameters: {
                type: 'object',
                properties: {
                  code: {
                    type: 'string',
                    description: 'Python code to run. Must include print() for output.'
                  }
                },
                required: ['code']
              }
            }
          }
        case 'search':
          return {
            type: 'function',
            function: {
              name: 'web_search',
              description: 'Search the web for information',
              parameters: {
                type: 'object',
                properties: {
                  query: {
                    type: 'string',
                    description: 'Search query'
                  }
                },
                required: ['query']
              }
            }
          }
        default:
          return null
      }
    }).filter(Boolean)
  }

  // Add custom functions if specified
  if (functions.length > 0) {
    if (!requestBody.tools) requestBody.tools = []
    functions.forEach(func => {
      requestBody.tools.push({
        type: 'function',
        function: {
          name: func.name,
          description: func.description || '',
          parameters: func.parameters || {}
        }
      })
    })
  }

  const response = await fetch(`${OPENROUTER_BASE_URL}/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`,
      'HTTP-Referer': window.location.origin,
      'X-Title': 'Dumont Cloud Agents'
    },
    body: JSON.stringify(requestBody)
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: { message: response.statusText } }))
    throw new Error(error.error?.message || `OpenRouter API error: ${response.status}`)
  }

  // Handle streaming response
  if (onStream && response.body) {
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let fullContent = ''
    let accumulatedToolCalls = []

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value, { stream: true })
      const lines = chunk.split('\n').filter(line => line.trim().startsWith('data: '))

      for (const line of lines) {
        const data = line.replace('data: ', '').trim()
        if (data === '[DONE]') continue

        try {
          const parsed = JSON.parse(data)
          const content = parsed.choices?.[0]?.delta?.content || ''
          if (content) {
            fullContent += content
            onStream(content, fullContent)
          }

          // Handle tool calls in streaming - accumulate them
          const toolCalls = parsed.choices?.[0]?.delta?.tool_calls
          if (toolCalls) {
            for (const tc of toolCalls) {
              const idx = tc.index || 0
              if (!accumulatedToolCalls[idx]) {
                accumulatedToolCalls[idx] = {
                  id: tc.id || `call_${idx}`,
                  type: 'function',
                  function: { name: '', arguments: '' }
                }
              }
              if (tc.function?.name) {
                accumulatedToolCalls[idx].function.name = tc.function.name
              }
              if (tc.function?.arguments) {
                accumulatedToolCalls[idx].function.arguments += tc.function.arguments
              }
            }
            onStream(null, fullContent, accumulatedToolCalls)
          }
        } catch (e) {
          // Ignore JSON parse errors for partial chunks
        }
      }
    }

    // Return accumulated tool calls if any
    return {
      choices: [{
        message: {
          role: 'assistant',
          content: fullContent,
          tool_calls: accumulatedToolCalls.length > 0 ? accumulatedToolCalls : undefined
        }
      }]
    }
  }

  // Handle non-streaming response
  return response.json()
}

/**
 * Get available models from OpenRouter
 */
export async function getAvailableModels() {
  const apiKey = getOpenRouterApiKey()

  if (!apiKey) {
    return []
  }

  try {
    const response = await fetch(`${OPENROUTER_BASE_URL}/models`, {
      headers: {
        'Authorization': `Bearer ${apiKey}`
      }
    })

    if (!response.ok) {
      return []
    }

    const data = await response.json()
    return data.data || []
  } catch (error) {
    console.error('Failed to fetch OpenRouter models:', error)
    return []
  }
}

export default {
  chatCompletion,
  getAvailableModels,
  getOpenRouterApiKey,
  setOpenRouterApiKey,
  hasOpenRouterApiKey
}
