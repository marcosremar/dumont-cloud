import React, { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  FiCpu,
  FiCode,
  FiImage,
  FiSearch,
  FiZap,
  FiPlus,
  FiSettings,
  FiMessageSquare,
  FiSend,
  FiX,
  FiCheck,
  FiChevronDown,
  FiPlay,
  FiTrash2,
  FiEdit3,
  FiCopy,
  FiExternalLink,
  FiInfo,
  FiSliders,
  FiFileText,
  FiGlobe,
  FiStar,
  FiServer,
  FiCloud,
  FiHelpCircle,
  FiTerminal,
  FiDatabase
} from 'react-icons/fi'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'react-markdown'

// =============================================================================
// COMPONENTE: Info Tooltip (como no Mistral)
// =============================================================================

function InfoTooltip({ text }) {
  const [show, setShow] = useState(false)

  return (
    <div className="relative inline-flex">
      <button
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        className="text-gray-500 hover:text-gray-400 transition-colors"
      >
        <FiHelpCircle size={12} />
      </button>
      <AnimatePresence>
        {show && (
          <motion.div
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 5 }}
            className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 px-3 py-2 bg-dark-surface-card border border-white/10 rounded-lg shadow-xl text-xs text-gray-300 whitespace-nowrap z-50"
          >
            {text}
            <div className="absolute left-1/2 -translate-x-1/2 top-full w-2 h-2 bg-dark-surface-card border-r border-b border-white/10 transform rotate-45 -mt-1" />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// =============================================================================
// COMPONENTE: Code Modal (mostra código da API)
// =============================================================================

function CodeModal({ isOpen, onClose, agentConfig }) {
  if (!isOpen) return null

  const code = `import openai

client = openai.OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="YOUR_API_KEY"
)

response = client.chat.completions.create(
    model="${agentConfig.model}",
    messages=[
        {"role": "system", "content": """${agentConfig.instructions || 'Your instructions here...'}"""},
        {"role": "user", "content": "Your message here..."}
    ],
    temperature=${agentConfig.params?.temperature || 0.7},
    max_tokens=${agentConfig.params?.max_tokens || 2048},
    top_p=${agentConfig.params?.top_p || 1}${agentConfig.tools?.length > 0 ? `,
    tools=[${agentConfig.tools.map(t => `"${t}"`).join(', ')}]` : ''}${agentConfig.responseFormat === 'json' ? `,
    response_format={"type": "json_object"}` : ''}
)

print(response.choices[0].message.content)`

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="relative bg-dark-surface-card border border-white/10 rounded-xl shadow-2xl w-full max-w-2xl mx-4 p-5"
      >
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/20 rounded-lg">
              <FiTerminal className="text-blue-400" size={20} />
            </div>
            <div>
              <h3 className="text-lg font-medium text-gray-200">API Code</h3>
              <p className="text-xs text-gray-500">Python code to use this agent via API</p>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300">
            <FiX size={20} />
          </button>
        </div>

        <div className="relative">
          <pre className="bg-dark-surface border border-white/10 rounded-lg p-4 overflow-x-auto text-sm text-gray-300 font-mono">
            <code>{code}</code>
          </pre>
          <button
            onClick={() => { navigator.clipboard.writeText(code); }}
            className="absolute top-2 right-2 p-2 bg-white/5 hover:bg-white/10 rounded-lg text-gray-400 hover:text-gray-200 transition-all"
            title="Copy to clipboard"
          >
            <FiCopy size={14} />
          </button>
        </div>

        <div className="flex justify-end mt-4">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 rounded-lg transition-all"
          >
            Close
          </button>
        </div>
      </motion.div>
    </div>
  )
}

// =============================================================================
// MODELOS DISPONÍVEIS
// =============================================================================

const AVAILABLE_MODELS = {
  openrouter: [
    { id: 'openai/gpt-4o', name: 'GPT-4o', provider: 'OpenAI', category: 'main' },
    { id: 'openai/gpt-4o-mini', name: 'GPT-4o Mini', provider: 'OpenAI', category: 'main' },
    { id: 'anthropic/claude-3.5-sonnet', name: 'Claude 3.5 Sonnet', provider: 'Anthropic', category: 'main' },
    { id: 'anthropic/claude-3-opus', name: 'Claude 3 Opus', provider: 'Anthropic', category: 'main' },
    { id: 'google/gemini-pro-1.5', name: 'Gemini Pro 1.5', provider: 'Google', category: 'main' },
    { id: 'z-ai/glm-4.7', name: 'GLM-4.7', provider: 'Z.AI', category: 'main' },
    { id: 'mistralai/mistral-large', name: 'Mistral Large', provider: 'Mistral', category: 'main' },
    { id: 'mistralai/mistral-medium', name: 'Mistral Medium', provider: 'Mistral', category: 'main' },
    { id: 'mistralai/mistral-small', name: 'Mistral Small', provider: 'Mistral', category: 'main' },
    { id: 'mistralai/codestral', name: 'Codestral', provider: 'Mistral', category: 'code' },
    { id: 'meta-llama/llama-3.1-70b', name: 'Llama 3.1 70B', provider: 'Meta', category: 'open' },
    { id: 'meta-llama/llama-3.1-8b', name: 'Llama 3.1 8B', provider: 'Meta', category: 'open' },
    { id: 'qwen/qwen-2.5-72b', name: 'Qwen 2.5 72B', provider: 'Alibaba', category: 'open' },
  ],
  serverless: [] // Preenchido dinamicamente com modelos deployados
}

const MODEL_CATEGORIES = {
  main: 'Principais',
  code: 'Código',
  open: 'Open Source',
  serverless: 'Seus Modelos'
}

// =============================================================================
// TOOLS DISPONÍVEIS
// =============================================================================

const AVAILABLE_TOOLS = [
  {
    id: 'code',
    name: 'Code',
    icon: FiCode,
    description: 'Enable the model to run code.',
    color: 'text-blue-400'
  },
  {
    id: 'image',
    name: 'Image',
    icon: FiImage,
    description: 'Enable the model to generate images.',
    color: 'text-purple-400'
  },
  {
    id: 'search',
    name: 'Search',
    icon: FiSearch,
    description: 'Enable the model to search the web.',
    color: 'text-green-400'
  },
  {
    id: 'premium_search',
    name: 'Premium Search',
    icon: FiStar,
    description: 'Enable the model to search the web and access verified news articles via integrated news provider verification for enhanced information retrieval.',
    color: 'text-yellow-400'
  }
]

// =============================================================================
// EXEMPLOS DE FUNCTIONS
// =============================================================================

const FUNCTION_EXAMPLES = [
  {
    name: 'get_weather',
    description: 'Obtém o clima atual de uma localização',
    parameters: {
      type: 'object',
      properties: {
        location: {
          type: 'string',
          description: 'A cidade e estado, ex: São Paulo, SP'
        }
      },
      required: ['location']
    }
  },
  {
    name: 'get_stock_price',
    description: 'Obtém o preço atual de uma ação',
    parameters: {
      type: 'object',
      properties: {
        symbol: {
          type: 'string',
          description: 'O símbolo da ação, ex: PETR4'
        }
      },
      required: ['symbol']
    }
  },
  {
    name: 'translate_text',
    description: 'Traduz texto para outro idioma',
    parameters: {
      type: 'object',
      properties: {
        text: { type: 'string', description: 'Texto a traduzir' },
        target_language: { type: 'string', description: 'Idioma de destino' }
      },
      required: ['text', 'target_language']
    }
  }
]

// =============================================================================
// COMPONENTE: Model Selector
// =============================================================================

function ModelSelector({ selectedModel, onSelect, serverlessModels = [] }) {
  const [isOpen, setIsOpen] = useState(false)
  const [search, setSearch] = useState('')
  const dropdownRef = useRef(null)

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const allModels = [
    ...AVAILABLE_MODELS.openrouter,
    ...serverlessModels.map(m => ({ ...m, category: 'serverless' }))
  ]

  const filteredModels = allModels.filter(m =>
    m.name.toLowerCase().includes(search.toLowerCase()) ||
    m.provider?.toLowerCase().includes(search.toLowerCase())
  )

  const groupedModels = filteredModels.reduce((acc, model) => {
    const cat = model.category || 'main'
    if (!acc[cat]) acc[cat] = []
    acc[cat].push(model)
    return acc
  }, {})

  const selected = allModels.find(m => m.id === selectedModel)

  return (
    <div ref={dropdownRef} className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 bg-dark-surface-card border border-white/10 rounded-lg hover:border-purple-500/50 transition-all min-w-[200px]"
      >
        {selected?.category === 'serverless' ? (
          <FiServer className="text-green-400" />
        ) : (
          <FiCloud className="text-purple-400" />
        )}
        <span className="text-gray-200 flex-1 text-left truncate">
          {selected?.name || 'Select a model'}
        </span>
        <FiChevronDown className={`text-gray-500 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute top-full mt-2 left-0 right-0 bg-dark-surface-card border border-white/10 rounded-lg shadow-xl z-50 max-h-[400px] overflow-hidden"
          >
            <div className="p-2 border-b border-white/10">
              <div className="flex items-center gap-2 px-2 py-1.5 bg-dark-surface rounded-md">
                <FiSearch className="text-gray-500" />
                <input
                  type="text"
                  placeholder="Search model..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="flex-1 bg-transparent text-sm text-gray-200 outline-none"
                  autoFocus
                />
              </div>
            </div>
            <div className="overflow-y-auto max-h-[340px] p-1">
              {Object.entries(groupedModels).map(([category, models]) => (
                <div key={category}>
                  <div className="px-3 py-2 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    {MODEL_CATEGORIES[category] || category}
                  </div>
                  {models.map(model => (
                    <button
                      key={model.id}
                      onClick={() => { onSelect(model.id); setIsOpen(false); setSearch(''); }}
                      className={`w-full flex items-center gap-3 px-3 py-2 rounded-md transition-all ${
                        selectedModel === model.id
                          ? 'bg-purple-500/20 text-purple-300'
                          : 'hover:bg-white/5 text-gray-300'
                      }`}
                    >
                      {model.category === 'serverless' ? (
                        <FiServer className="text-green-400" />
                      ) : (
                        <FiCloud className="text-purple-400/50" />
                      )}
                      <div className="flex-1 text-left">
                        <div className="text-sm">{model.name}</div>
                        {model.provider && (
                          <div className="text-xs text-gray-500">{model.provider}</div>
                        )}
                      </div>
                      {selectedModel === model.id && (
                        <FiCheck className="text-purple-400" />
                      )}
                    </button>
                  ))}
                </div>
              ))}
              {Object.keys(groupedModels).length === 0 && (
                <div className="px-3 py-4 text-center text-gray-500 text-sm">
                  No models found
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// =============================================================================
// COMPONENTE: Parameters Panel
// =============================================================================

function ParametersPanel({ params, onChange }) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 bg-dark-surface-card border border-white/10 rounded-lg hover:border-white/20 transition-all text-xs text-gray-400"
      >
        <span>temperature: {params.temperature}</span>
        <span className="text-white/20">|</span>
        <span>max_tokens: {params.max_tokens}</span>
        <span className="text-white/20">|</span>
        <span>top_p: {params.top_p}</span>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute top-full mt-2 left-0 bg-dark-surface-card border border-white/10 rounded-lg shadow-xl z-50 p-4 min-w-[280px]"
          >
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-xs mb-2">
                  <span className="text-gray-400">Temperature</span>
                  <span className="text-gray-200">{params.temperature}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={params.temperature}
                  onChange={(e) => onChange({ ...params, temperature: parseFloat(e.target.value) })}
                  className="w-full accent-purple-500"
                />
              </div>
              <div>
                <div className="flex justify-between text-xs mb-2">
                  <span className="text-gray-400">Max Tokens</span>
                  <span className="text-gray-200">{params.max_tokens}</span>
                </div>
                <input
                  type="range"
                  min="256"
                  max="8192"
                  step="256"
                  value={params.max_tokens}
                  onChange={(e) => onChange({ ...params, max_tokens: parseInt(e.target.value) })}
                  className="w-full accent-purple-500"
                />
              </div>
              <div>
                <div className="flex justify-between text-xs mb-2">
                  <span className="text-gray-400">Top P</span>
                  <span className="text-gray-200">{params.top_p}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={params.top_p}
                  onChange={(e) => onChange({ ...params, top_p: parseFloat(e.target.value) })}
                  className="w-full accent-purple-500"
                />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// =============================================================================
// COMPONENTE: Tools Selector
// =============================================================================

function ToolsSelector({ selectedTools, onToggle }) {
  return (
    <div className="flex items-center gap-1">
      {AVAILABLE_TOOLS.map(tool => {
        const Icon = tool.icon
        const isSelected = selectedTools.includes(tool.id)
        return (
          <button
            key={tool.id}
            onClick={() => onToggle(tool.id)}
            title={`${tool.name}: ${tool.description}`}
            className={`p-2 rounded-lg transition-all ${
              isSelected
                ? `bg-white/10 ${tool.color}`
                : 'bg-dark-surface-card text-gray-500 hover:text-gray-300 hover:bg-white/5'
            }`}
          >
            <Icon size={16} />
          </button>
        )
      })}
    </div>
  )
}

// =============================================================================
// COMPONENTE: Functions Editor
// =============================================================================

function FunctionsEditor({ functions, onAdd, onRemove, onUpdate }) {
  const [showAddModal, setShowAddModal] = useState(false)
  const [newFunc, setNewFunc] = useState({ name: '', description: '', parameters: '', strict: true })
  const [showExamples, setShowExamples] = useState(false)

  const handleAddFunction = () => {
    if (!newFunc.name) return
    try {
      const params = newFunc.parameters ? JSON.parse(newFunc.parameters) : {}
      onAdd({
        name: newFunc.name,
        description: newFunc.description,
        parameters: params,
        strict: newFunc.strict
      })
      setNewFunc({ name: '', description: '', parameters: '', strict: true })
      setShowAddModal(false)
    } catch (e) {
      alert('Invalid JSON in parameters')
    }
  }

  const loadExample = (example) => {
    setNewFunc({
      name: example.name,
      description: example.description,
      parameters: JSON.stringify(example.parameters, null, 2),
      strict: true
    })
    setShowExamples(false)
  }

  return (
    <div>
      <div className="flex items-center gap-2">
        <button
          onClick={() => setShowAddModal(true)}
          className="p-2 bg-dark-surface-card rounded-lg text-gray-500 hover:text-purple-400 hover:bg-white/5 transition-all"
        >
          <FiPlus size={16} />
        </button>
        {functions.length > 0 && (
          <span className="text-xs text-gray-500">{functions.length} function(s)</span>
        )}
      </div>

      {/* Lista de funções */}
      {functions.length > 0 && (
        <div className="mt-2 space-y-1">
          {functions.map((func, idx) => (
            <div key={idx} className="flex items-center gap-2 px-2 py-1 bg-dark-surface rounded text-xs">
              <FiCode className="text-blue-400" />
              <span className="text-gray-300 flex-1">{func.name}</span>
              <button onClick={() => onRemove(idx)} className="text-gray-500 hover:text-red-400">
                <FiX size={12} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Modal para adicionar função */}
      <AnimatePresence>
        {showAddModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setShowAddModal(false)} />
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="relative bg-dark-surface-card border border-white/10 rounded-xl shadow-2xl w-full max-w-lg mx-4 p-5"
            >
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-medium text-gray-200">Add Function</h3>
                  <p className="text-xs text-gray-500 mt-1">
                    Define functions that the model can call.{' '}
                    <a href="https://docs.mistral.ai/capabilities/function_calling/" target="_blank" rel="noopener" className="text-purple-400 hover:underline">
                      Learn more
                    </a>
                  </p>
                </div>
                <div className="relative">
                  <button
                    onClick={() => setShowExamples(!showExamples)}
                    className="px-3 py-1.5 text-xs bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 transition-all flex items-center gap-1"
                  >
                    Examples <FiChevronDown />
                  </button>
                  {showExamples && (
                    <div className="absolute top-full right-0 mt-1 bg-dark-surface border border-white/10 rounded-lg shadow-xl z-10 py-1 min-w-[150px]">
                      {FUNCTION_EXAMPLES.map(ex => (
                        <button
                          key={ex.name}
                          onClick={() => loadExample(ex)}
                          className="w-full px-3 py-2 text-left text-sm text-gray-300 hover:bg-white/5"
                        >
                          {ex.name}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Name</label>
                  <input
                    type="text"
                    placeholder="e.g. get_weather"
                    value={newFunc.name}
                    onChange={(e) => setNewFunc({ ...newFunc, name: e.target.value })}
                    className="w-full px-3 py-2 bg-dark-surface border border-white/10 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-brand-500/50"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Description <span className="text-gray-600">(optional)</span></label>
                  <input
                    type="text"
                    placeholder="e.g. Get current weather for a location"
                    value={newFunc.description}
                    onChange={(e) => setNewFunc({ ...newFunc, description: e.target.value })}
                    className="w-full px-3 py-2 bg-dark-surface border border-white/10 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-brand-500/50"
                  />
                </div>
                <div className="flex items-center gap-3">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={newFunc.strict}
                      onChange={(e) => setNewFunc({ ...newFunc, strict: e.target.checked })}
                      className="accent-purple-500"
                    />
                    <span className="text-sm text-gray-300">Strict</span>
                  </label>
                  <span className="text-xs text-gray-500">Ensures response follows the schema</span>
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Parameters (JSON Schema)</label>
                  <textarea
                    placeholder='{"type": "object", "properties": {...}}'
                    value={newFunc.parameters}
                    onChange={(e) => setNewFunc({ ...newFunc, parameters: e.target.value })}
                    rows={6}
                    className="w-full px-3 py-2 bg-dark-surface border border-white/10 rounded-lg text-sm text-gray-200 font-mono focus:outline-none focus:border-brand-500/50 resize-none"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 mt-5">
                <button
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-sm text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 rounded-lg transition-all"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAddFunction}
                  disabled={!newFunc.name}
                  className="px-4 py-2 text-sm text-white bg-purple-600 hover:bg-purple-500 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Add
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}

// =============================================================================
// COMPONENTE: Response Format Selector
// =============================================================================

function ResponseFormatSelector({ format, onChange }) {
  const [isOpen, setIsOpen] = useState(false)
  const formats = [
    { id: 'text', name: 'Text', description: 'Free-form text response' },
    { id: 'json', name: 'JSON', description: 'Structured JSON response' }
  ]

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 bg-dark-surface-card border border-white/10 rounded-lg hover:border-white/20 transition-all min-w-[100px]"
      >
        <span className="text-gray-200 text-sm">{format === 'json' ? 'JSON' : 'Text'}</span>
        <FiChevronDown className="text-gray-500" />
      </button>
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute top-full mt-2 left-0 bg-dark-surface-card border border-white/10 rounded-lg shadow-xl z-50 py-1 min-w-[180px]"
          >
            {formats.map(f => (
              <button
                key={f.id}
                onClick={() => { onChange(f.id); setIsOpen(false); }}
                className={`w-full px-3 py-2 text-left flex items-center gap-2 ${
                  format === f.id ? 'bg-purple-500/20 text-purple-300' : 'hover:bg-white/5 text-gray-300'
                }`}
              >
                <div>
                  <div className="text-sm">{f.name}</div>
                  <div className="text-xs text-gray-500">{f.description}</div>
                </div>
                {format === f.id && <FiCheck className="ml-auto text-purple-400" />}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// =============================================================================
// COMPONENTE: Create Agent Modal
// =============================================================================

// Memory Provider Options
const MEMORY_PROVIDERS = [
  {
    id: 'gcp',
    name: 'Google Cloud',
    description: 'Vertex AI Embeddings + Vector Search',
    icon: '🔷',
    available: true
  },
  {
    id: 'pinecone',
    name: 'Pinecone',
    description: 'High-performance vector database',
    icon: '🌲',
    available: false // Future
  },
  {
    id: 'chroma',
    name: 'Chroma',
    description: 'Open-source, self-hosted',
    icon: '🎨',
    available: false // Future
  }
]

function CreateAgentModal({ isOpen, onClose, onCreate, agentConfig }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [enableMemory, setEnableMemory] = useState(false)
  const [memoryProvider, setMemoryProvider] = useState('gcp')
  const [showProviderDropdown, setShowProviderDropdown] = useState(false)

  const handleCreate = () => {
    if (!name) return
    onCreate({
      name,
      description,
      config: agentConfig,
      memory: enableMemory ? {
        enabled: true,
        provider: memoryProvider
      } : null
    })
    setName('')
    setDescription('')
    setEnableMemory(false)
    setMemoryProvider('gcp')
    onClose()
  }

  if (!isOpen) return null

  const selectedProvider = MEMORY_PROVIDERS.find(p => p.id === memoryProvider)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="relative bg-dark-surface-card border border-white/10 rounded-xl shadow-2xl w-full max-w-md mx-4 p-5"
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-purple-500/20 rounded-lg">
            <FiCpu className="text-purple-400" size={20} />
          </div>
          <div>
            <h3 className="text-lg font-medium text-gray-200">Create Agent</h3>
            <p className="text-xs text-gray-500">Create a new agent with the current settings</p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-xs text-gray-400 block mb-1">Agent Name</label>
            <input
              type="text"
              placeholder="Enter agent name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 bg-dark-surface border border-white/10 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-brand-500/50"
              autoFocus
            />
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Description</label>
            <input
              type="text"
              placeholder="Enter agent description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 bg-dark-surface border border-white/10 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-brand-500/50"
            />
          </div>

          {/* Memory Toggle */}
          <div className="border-t border-white/10 pt-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <FiDatabase className={enableMemory ? 'text-green-400' : 'text-gray-500'} size={16} />
                <span className="text-sm text-gray-300">Enable Memory</span>
              </div>
              <button
                onClick={() => setEnableMemory(!enableMemory)}
                className={`relative w-11 h-6 rounded-full transition-colors ${
                  enableMemory ? 'bg-green-500' : 'bg-gray-600'
                }`}
              >
                <span
                  className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                    enableMemory ? 'left-6' : 'left-1'
                  }`}
                />
              </button>
            </div>

            {enableMemory && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="space-y-3"
              >
                <p className="text-xs text-gray-500">
                  Memory allows the agent to remember facts, preferences, and conversation history across sessions.
                </p>

                {/* Provider Selector */}
                <div className="relative">
                  <label className="text-xs text-gray-400 block mb-1">Memory Provider</label>
                  <button
                    onClick={() => setShowProviderDropdown(!showProviderDropdown)}
                    className="w-full flex items-center justify-between px-3 py-2 bg-dark-surface border border-white/10 rounded-lg text-sm text-gray-200 hover:border-white/20"
                  >
                    <div className="flex items-center gap-2">
                      <span>{selectedProvider?.icon}</span>
                      <span>{selectedProvider?.name}</span>
                    </div>
                    <FiChevronDown className={`text-gray-500 transition-transform ${showProviderDropdown ? 'rotate-180' : ''}`} />
                  </button>

                  <AnimatePresence>
                    {showProviderDropdown && (
                      <motion.div
                        initial={{ opacity: 0, y: -5 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -5 }}
                        className="absolute top-full left-0 right-0 mt-1 bg-dark-surface border border-white/10 rounded-lg shadow-xl z-10 overflow-hidden"
                      >
                        {MEMORY_PROVIDERS.map(provider => (
                          <button
                            key={provider.id}
                            onClick={() => {
                              if (provider.available) {
                                setMemoryProvider(provider.id)
                                setShowProviderDropdown(false)
                              }
                            }}
                            disabled={!provider.available}
                            className={`w-full flex items-center gap-3 px-3 py-2 text-left transition-all ${
                              provider.available
                                ? memoryProvider === provider.id
                                  ? 'bg-green-500/20 text-green-300'
                                  : 'hover:bg-white/5 text-gray-300'
                                : 'opacity-50 cursor-not-allowed text-gray-500'
                            }`}
                          >
                            <span className="text-lg">{provider.icon}</span>
                            <div className="flex-1">
                              <div className="text-sm flex items-center gap-2">
                                {provider.name}
                                {!provider.available && (
                                  <span className="text-[10px] px-1.5 py-0.5 bg-gray-700 rounded text-gray-400">
                                    Em breve
                                  </span>
                                )}
                              </div>
                              <div className="text-xs text-gray-500">{provider.description}</div>
                            </div>
                            {memoryProvider === provider.id && provider.available && (
                              <FiCheck className="text-green-400" />
                            )}
                          </button>
                        ))}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

                <div className="flex items-center gap-2 p-2 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                  <FiInfo className="text-blue-400 shrink-0" size={14} />
                  <p className="text-xs text-blue-300">
                    Using GCP Vertex AI for embeddings. Make sure GCP credentials are configured.
                  </p>
                </div>
              </motion.div>
            )}
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-5">
          <button
            onClick={onClose}
            className="ta-btn ta-btn-secondary"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={!name}
            className="ta-btn ta-btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <FiPlus size={14} />
            Create Agent
          </button>
        </div>
      </motion.div>
    </div>
  )
}

// =============================================================================
// COMPONENTE: Agents List
// =============================================================================

function AgentsList({ agents, onSelect, onDelete, selectedAgentId }) {
  if (agents.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <FiCpu size={40} className="mx-auto mb-3 opacity-50" />
        <p>No agents created</p>
        <p className="text-xs mt-1">Configure an agent in Playground and click "Create Agent"</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="text-left text-xs text-gray-500 border-b border-white/10">
            <th className="pb-3 font-medium">Name</th>
            <th className="pb-3 font-medium">Model</th>
            <th className="pb-3 font-medium">Created</th>
            <th className="pb-3 font-medium">API ID</th>
            <th className="pb-3 font-medium w-10"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {agents.map(agent => (
            <tr
              key={agent.id}
              onClick={() => onSelect(agent)}
              className={`cursor-pointer transition-all ${
                selectedAgentId === agent.id ? 'bg-purple-500/10' : 'hover:bg-white/5'
              }`}
            >
              <td className="py-3">
                <div className="font-medium text-gray-200">{agent.name}</div>
                <div className="text-xs text-gray-500">{agent.description || 'No description'}</div>
              </td>
              <td className="py-3 text-sm text-gray-400">{agent.config?.model || '-'}</td>
              <td className="py-3 text-sm text-gray-500">
                {new Date(agent.created_at).toLocaleDateString('pt-BR')}
              </td>
              <td className="py-3">
                <code className="text-xs bg-white/5 px-2 py-1 rounded text-gray-400">
                  {agent.id?.substring(0, 12)}...
                </code>
              </td>
              <td className="py-3">
                <button
                  onClick={(e) => { e.stopPropagation(); onDelete(agent.id); }}
                  className="p-1.5 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded transition-all"
                >
                  <FiTrash2 size={14} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// =============================================================================
// COMPONENTE: Code Execution Result
// =============================================================================

function CodeExecutionResult({ result, code }) {
  if (!result) return null

  // Check if output contains base64 image
  const imageMatch = result.output?.match(/data:image\/(png|jpeg|jpg|gif|webp);base64,[A-Za-z0-9+/=]+/)
  const hasImage = imageMatch !== null

  // Check if output contains base64 audio
  const audioMatch = result.output?.match(/data:audio\/(wav|mp3|ogg|webm);base64,[A-Za-z0-9+/=]+/)
  const hasAudio = audioMatch !== null

  // Clean output (remove base64 data for display)
  let cleanOutput = result.output || ''
  if (hasImage) {
    cleanOutput = cleanOutput.replace(/data:image\/[^;]+;base64,[A-Za-z0-9+/=]+/g, '[Image rendered below]')
  }
  if (hasAudio) {
    cleanOutput = cleanOutput.replace(/data:audio\/[^;]+;base64,[A-Za-z0-9+/=]+/g, '[Audio rendered below]')
  }

  return (
    <div className="mt-2 p-3 bg-dark-surface rounded-lg border border-white/10">
      {/* Header */}
      <div className="flex items-center gap-2 mb-2 text-xs text-gray-500">
        <FiTerminal size={12} />
        <span>Python Execution ({result.executionTime}ms)</span>
        {result.success ? (
          <span className="text-green-400">✓ Success</span>
        ) : (
          <span className="text-red-400">✗ Error</span>
        )}
      </div>

      {/* Code that was executed */}
      {code && (
        <div className="mb-3">
          <div className="text-xs text-gray-500 mb-1 flex items-center gap-1">
            <FiCode size={10} />
            <span>Code:</span>
          </div>
          <pre className="text-xs text-blue-300 font-mono whitespace-pre-wrap bg-blue-900/20 p-2 rounded border border-blue-500/20 max-h-32 overflow-auto">
            {code}
          </pre>
        </div>
      )}

      {/* Output */}
      {cleanOutput && cleanOutput.trim() && (
        <div className="mb-2">
          <div className="text-xs text-gray-500 mb-1">Output:</div>
          <pre className="text-xs text-green-300 font-mono whitespace-pre-wrap bg-green-900/20 p-2 rounded border border-green-500/20">
            {cleanOutput.trim()}
          </pre>
        </div>
      )}

      {/* No output message */}
      {result.success && !cleanOutput?.trim() && !hasImage && !hasAudio && (
        <div className="text-xs text-gray-500 italic">
          Code executed successfully (no output)
        </div>
      )}

      {/* Error */}
      {result.error && (
        <div className="mb-2">
          <div className="text-xs text-red-400 mb-1">Error:</div>
          <pre className="text-xs text-red-300 font-mono whitespace-pre-wrap bg-red-900/20 p-2 rounded border border-red-500/20">
            {result.error}
          </pre>
        </div>
      )}

      {/* Rendered Image */}
      {hasImage && (
        <div className="mt-2">
          <div className="text-xs text-gray-500 mb-1">Generated Image:</div>
          <img
            src={imageMatch[0]}
            alt="Generated output"
            className="max-w-full rounded border border-white/10"
          />
        </div>
      )}

      {/* Rendered Audio */}
      {hasAudio && (
        <div className="mt-2">
          <div className="text-xs text-gray-500 mb-1">Generated Audio:</div>
          <audio controls className="w-full">
            <source src={audioMatch[0]} />
            Your browser does not support the audio element.
          </audio>
        </div>
      )}
    </div>
  )
}

// =============================================================================
// HELPER: Parse tool calls from various formats (native, XML tags, markdown)
// Supports both native LLM tool_calls AND text-based patterns
// =============================================================================

function parseXmlToolCalls(content) {
  if (!content || typeof content !== 'string') return null

  const toolCalls = []
  let match

  // =========================================================================
  // FORMAT 1: XML <tool_call> tags with function name and JSON args
  // Example: <tool_call>execute_code{"code": "print(1)"}</tool_call>
  // =========================================================================
  const format1Regex = /<tool_call>\s*(\w+)\s*(\{[\s\S]*?\})\s*<\/tool_call>/gi
  while ((match = format1Regex.exec(content)) !== null) {
    try {
      const args = JSON.parse(match[2])
      toolCalls.push({
        function: { name: match[1], arguments: JSON.stringify(args) }
      })
    } catch (e) {
      console.warn('Failed to parse tool call arguments:', e)
    }
  }

  // =========================================================================
  // FORMAT 2: XML <tool_call> with JSON object containing name
  // Example: <tool_call>{"name": "execute_code", "arguments": {...}}</tool_call>
  // =========================================================================
  if (toolCalls.length === 0) {
    const format2Regex = /<tool_call>\s*(\{[\s\S]*?\})\s*<\/tool_call>/gi
    while ((match = format2Regex.exec(content)) !== null) {
      try {
        const parsed = JSON.parse(match[1])
        if (parsed.name) {
          toolCalls.push({
            function: {
              name: parsed.name,
              arguments: JSON.stringify(parsed.arguments || parsed.parameters || {})
            }
          })
        }
      } catch (e) {
        // Ignore parse errors
      }
    }
  }

  // =========================================================================
  // SKIP markdown code detection if response looks like an explanation
  // (contains numbered lists, tutorials, documentation, etc.)
  // =========================================================================

  // Count how many code blocks are in the content
  const codeBlockMatches = content.match(/```/g)
  const codeBlockCount = codeBlockMatches ? Math.floor(codeBlockMatches.length / 2) : 0

  // Check for various explanation patterns
  const hasNumberedList = /\d+\.\s+\*?\*?[A-Za-zÀ-ÿ]/.test(content) // "1. Something" or "1. **Something"
  const hasBulletList = content.includes('- ') && content.split('- ').length > 2
  const hasMultipleCodeBlocks = codeBlockCount > 1
  const hasExplanationPhrases = (
    content.includes('Aqui está') ||
    content.includes('Here is') ||
    content.includes('Here\'s') ||
    content.includes('exemplo') ||
    content.includes('example') ||
    content.includes('Instalar') ||
    content.includes('Install') ||
    content.includes('Chamar a função') ||
    content.includes('Call the function') ||
    content.includes('Explicação') ||
    content.includes('Explanation') ||
    content.includes('você pode') ||
    content.includes('you can') ||
    content.includes('Para criar') ||
    content.includes('To create') ||
    content.includes('Primeiro') ||
    content.includes('First') ||
    content.includes('biblioteca') ||
    content.includes('library') ||
    content.includes('passo') ||
    content.includes('step')
  )

  // Calculate total text outside code blocks
  const textOutsideCode = content.replace(/```[\s\S]*?```/g, '').trim()
  const hasLongExplanation = textOutsideCode.length > 200

  const isExplanation = (
    hasNumberedList ||
    hasBulletList ||
    hasMultipleCodeBlocks ||
    hasExplanationPhrases ||
    hasLongExplanation
  )

  if (isExplanation) {
    // Don't auto-execute code from explanations/tutorials
    console.log('parseXmlToolCalls: Skipping auto-execution - detected explanation content')
    return toolCalls.length > 0 ? toolCalls : null
  }

  // =========================================================================
  // FORMAT 3: Markdown Python code blocks (```python ... ```)
  // Only when NOT an explanation - for simple direct code responses
  // =========================================================================
  if (toolCalls.length === 0) {
    const pythonBlockRegex = /```(?:python|py)\s*\n([\s\S]*?)```/gi
    const matches = []
    while ((match = pythonBlockRegex.exec(content)) !== null) {
      matches.push(match[1].trim())
    }

    // Only auto-execute if there's exactly ONE code block and minimal surrounding text
    if (matches.length === 1) {
      const code = matches[0]
      const textWithoutCode = content.replace(/```[\s\S]*?```/g, '').trim()

      // Only execute if the surrounding text is minimal (< 100 chars)
      if (textWithoutCode.length < 100 && code && (
        code.includes('print') ||
        code.includes('def ') ||
        code.includes('for ') ||
        code.includes('while ') ||
        code.includes('import ') ||
        code.includes('=')
      )) {
        toolCalls.push({
          function: {
            name: 'execute_code',
            arguments: JSON.stringify({ code })
          }
        })
      }
    }
  }

  // =========================================================================
  // FORMAT 4: Inline code with print() or math expressions
  // Example: `print(2 + 2)` or `2 + 2`
  // =========================================================================
  if (toolCalls.length === 0) {
    // Look for inline code that looks like it should be executed
    const inlineCodeRegex = /`(print\([^`]+\))`/gi
    while ((match = inlineCodeRegex.exec(content)) !== null) {
      const code = match[1].trim()
      if (code) {
        toolCalls.push({
          function: {
            name: 'execute_code',
            arguments: JSON.stringify({ code })
          }
        })
      }
    }
  }

  // =========================================================================
  // FORMAT 5: Malformed tool_call tags with JSON code
  // Example: <tool_call>{"code": "..."}</tool_call>
  // =========================================================================
  if (toolCalls.length === 0 && content.includes('<tool_call>')) {
    const jsonMatch = content.match(/\{\s*"code"\s*:\s*"([\s\S]*?)"\s*\}/i)
    if (jsonMatch) {
      toolCalls.push({
        function: {
          name: 'execute_code',
          arguments: JSON.stringify({
            code: jsonMatch[1].replace(/\\n/g, '\n').replace(/\\"/g, '"')
          })
        }
      })
    }
  }

  // =========================================================================
  // FORMAT 6: GLM-style incomplete tags (common with streaming)
  // Example: <tool_call><tool_call>execute_code...
  // =========================================================================
  if (toolCalls.length === 0 && content.includes('<tool_call>')) {
    // Try to extract any code-like content after tool_call mentions
    const glmMatch = content.match(/execute_code[\s\S]*?["']code["']\s*:\s*["']([\s\S]*?)["']/i)
    if (glmMatch) {
      toolCalls.push({
        function: {
          name: 'execute_code',
          arguments: JSON.stringify({
            code: glmMatch[1].replace(/\\n/g, '\n').replace(/\\"/g, '"')
          })
        }
      })
    }
  }

  console.log('parseXmlToolCalls result:', toolCalls.length > 0 ? toolCalls : 'no tool calls found')
  return toolCalls.length > 0 ? toolCalls : null
}

// =============================================================================
// COMPONENTE: Chat Playground
// =============================================================================

function ChatPlayground({ agentConfig, disabled, hasApiKey, onNeedApiKey }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [pyodideStatus, setPyodideStatus] = useState('not_loaded')
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, streamingContent])

  // Preload Pyodide if code tool is enabled
  useEffect(() => {
    if (agentConfig.tools?.includes('code')) {
      import('../services/pythonSandbox').then(({ preloadPyodide, getPyodideStatus }) => {
        preloadPyodide()
        const checkStatus = setInterval(() => {
          const status = getPyodideStatus()
          setPyodideStatus(status)
          if (status === 'ready') clearInterval(checkStatus)
        }, 500)
        return () => clearInterval(checkStatus)
      })
    }
  }, [agentConfig.tools])

  const executeCode = async (code) => {
    const { executePython } = await import('../services/pythonSandbox')
    return executePython(code)
  }

  const sendMessage = async () => {
    if (!input.trim() || isLoading || disabled) return

    // Check for API key
    if (!hasApiKey) {
      onNeedApiKey?.()
      return
    }

    const userMessage = { role: 'user', content: input }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)
    setStreamingContent('')

    try {
      const { chatCompletion } = await import('../services/openRouterApi')

      // Build messages with system prompt
      const apiMessages = []
      if (agentConfig.instructions) {
        apiMessages.push({ role: 'system', content: agentConfig.instructions })
      }
      apiMessages.push(...messages.filter(m => m.role !== 'tool_result').map(m => ({
        role: m.role,
        content: m.content
      })))
      apiMessages.push({ role: 'user', content: input })

      // Make API call with streaming
      const response = await chatCompletion({
        model: agentConfig.model,
        messages: apiMessages,
        temperature: agentConfig.params?.temperature || 0.7,
        max_tokens: agentConfig.params?.max_tokens || 2048,
        top_p: agentConfig.params?.top_p || 1,
        responseFormat: agentConfig.responseFormat,
        tools: agentConfig.tools || [],
        functions: agentConfig.functions || [],
        onStream: (chunk, fullContent) => {
          setStreamingContent(fullContent)
        }
      })

      const assistantMessage = response.choices?.[0]?.message
      if (!assistantMessage) {
        throw new Error('No response from model')
      }

      // Handle tool calls (function calling) - native format or XML/markdown format
      let toolCallsToProcess = assistantMessage.tool_calls || []

      // If no native tool calls AND Code tool is enabled, try to parse from content
      const codeToolEnabled = agentConfig.tools?.includes('code')
      if (toolCallsToProcess.length === 0 && assistantMessage.content && codeToolEnabled) {
        const xmlToolCalls = parseXmlToolCalls(assistantMessage.content)
        if (xmlToolCalls) {
          toolCallsToProcess = xmlToolCalls
        }
      }

      if (toolCallsToProcess.length > 0) {
        const toolResults = []

        for (const toolCall of toolCallsToProcess) {
          const funcName = toolCall.function?.name
          let funcArgs = {}
          try {
            funcArgs = JSON.parse(toolCall.function?.arguments || '{}')
          } catch (e) {
            console.warn('Failed to parse tool call arguments:', e)
          }

          if (funcName === 'execute_code' && funcArgs.code) {
            // Execute Python code in sandbox
            const result = await executeCode(funcArgs.code)
            toolResults.push({
              role: 'tool_result',
              name: funcName,
              content: result.output || result.error,
              codeResult: result,
              executedCode: funcArgs.code
            })
          } else {
            // Other tool calls - placeholder
            toolResults.push({
              role: 'tool_result',
              name: funcName,
              content: `Tool "${funcName}" called with: ${JSON.stringify(funcArgs)}`
            })
          }
        }

        // Add assistant message with tool calls
        // Clean the content if it contains XML tool call tags
        let cleanContent = assistantMessage.content || 'Executing code...'
        if (cleanContent.includes('<tool_call>')) {
          cleanContent = cleanContent.replace(/<tool_call>[\s\S]*?<\/tool_call>/gi, '').trim()
          if (!cleanContent) cleanContent = 'Executing code...'
        }

        setMessages(prev => [...prev, {
          role: 'assistant',
          content: cleanContent,
          tool_calls: toolCallsToProcess
        }])

        // Add tool results
        for (const result of toolResults) {
          setMessages(prev => [...prev, result])
        }
      } else {
        // Regular response
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: assistantMessage.content || streamingContent
        }])
      }

      setStreamingContent('')
    } catch (error) {
      console.error('Error sending message:', error)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${error.message}`,
        isError: true
      }])
    } finally {
      setIsLoading(false)
      setStreamingContent('')
    }
  }

  const clearChat = () => {
    setMessages([])
    setStreamingContent('')
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/10">
        <div className="flex items-center gap-2">
          <button
            onClick={clearChat}
            className="p-1.5 text-gray-500 hover:text-gray-300 hover:bg-white/5 rounded transition-all"
            title="Clear chat"
          >
            <FiTrash2 size={14} />
          </button>
          {agentConfig.tools?.includes('code') && (
            <span className={`text-xs px-2 py-0.5 rounded ${
              pyodideStatus === 'ready' ? 'bg-green-500/20 text-green-400' :
              pyodideStatus === 'loading' ? 'bg-yellow-500/20 text-yellow-400' :
              'bg-gray-500/20 text-gray-400'
            }`}>
              {pyodideStatus === 'ready' ? 'Python Ready' :
               pyodideStatus === 'loading' ? 'Loading Python...' :
               'Python'}
            </span>
          )}
        </div>
        <button
          disabled
          className="flex items-center gap-2 px-3 py-1.5 text-xs bg-white/5 rounded-lg text-gray-500"
        >
          <FiPlus size={12} />
          New Chat
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!hasApiKey && (
          <div className="flex items-center gap-3 p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
            <FiInfo className="text-yellow-400 shrink-0" />
            <div className="flex-1">
              <p className="text-sm text-yellow-200">API Key Required</p>
              <p className="text-xs text-yellow-200/60">Add your OpenRouter API key to start chatting.</p>
            </div>
            <button
              onClick={onNeedApiKey}
              className="px-3 py-1.5 text-xs bg-yellow-500/20 hover:bg-yellow-500/30 text-yellow-300 rounded-lg transition-all"
            >
              Add Key
            </button>
          </div>
        )}

        {disabled && hasApiKey && (
          <div className="flex items-center gap-3 p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
            <FiInfo className="text-yellow-400 shrink-0" />
            <div>
              <p className="text-sm text-yellow-200">Chat disabled</p>
              <p className="text-xs text-yellow-200/60">Select a model to start chatting.</p>
            </div>
          </div>
        )}

        {messages.length === 0 && !disabled && hasApiKey && (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <FiMessageSquare size={32} className="mx-auto mb-2 opacity-50" />
              <p className="text-sm">Start a new chat</p>
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx}>
            {msg.role === 'tool_result' ? (
              <div className="flex justify-start">
                <div className="max-w-[90%]">
                  {msg.codeResult ? (
                    <CodeExecutionResult result={msg.codeResult} code={msg.executedCode} />
                  ) : (
                    <div className="px-4 py-2 rounded-lg bg-blue-900/20 border border-blue-500/20">
                      <div className="flex items-center gap-2 text-xs text-blue-400 mb-1">
                        <FiCode size={12} />
                        <span>Function: {msg.name}</span>
                      </div>
                      <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap">{msg.content}</pre>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[80%] px-4 py-2 rounded-lg ${
                    msg.role === 'user'
                      ? 'bg-purple-600 text-white'
                      : msg.isError
                        ? 'bg-red-900/20 text-red-300 border border-red-500/20'
                        : 'bg-dark-surface-card text-gray-200 border border-white/10'
                  }`}
                >
                  <div className="text-sm prose prose-invert prose-sm max-w-none">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}

        {/* Streaming content */}
        {streamingContent && (
          <div className="flex justify-start">
            <div className="max-w-[80%] px-4 py-2 rounded-lg bg-dark-surface-card text-gray-200 border border-white/10">
              <div className="text-sm prose prose-invert prose-sm max-w-none">
                <ReactMarkdown>{streamingContent}</ReactMarkdown>
              </div>
            </div>
          </div>
        )}

        {isLoading && !streamingContent && (
          <div className="flex justify-start">
            <div className="px-4 py-3 bg-dark-surface-card border border-white/10 rounded-lg">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-white/10">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
            placeholder={hasApiKey ? "Type a message..." : "Add API key to chat..."}
            disabled={disabled || isLoading || !hasApiKey}
            className="flex-1 px-4 py-2.5 bg-dark-surface border border-white/10 rounded-lg text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-brand-500/50 disabled:opacity-50"
          />
          <button
            onClick={sendMessage}
            disabled={disabled || isLoading || !input.trim() || !hasApiKey}
            className="p-2.5 bg-purple-600 hover:bg-purple-500 rounded-lg text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <FiSend size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// COMPONENTE: API Key Modal
// =============================================================================

function ApiKeyModal({ isOpen, onClose, currentKey, onSave }) {
  const [apiKey, setApiKey] = useState(currentKey || '')
  const [showKey, setShowKey] = useState(false)

  useEffect(() => {
    setApiKey(currentKey || '')
  }, [currentKey, isOpen])

  const handleSave = () => {
    onSave(apiKey.trim())
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="relative bg-dark-surface-card border border-white/10 rounded-xl shadow-2xl w-full max-w-md mx-4 p-5"
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-blue-500/20 rounded-lg">
            <FiSettings className="text-blue-400" size={20} />
          </div>
          <div>
            <h3 className="text-lg font-medium text-gray-200">OpenRouter API Key</h3>
            <p className="text-xs text-gray-500">Required for chat functionality</p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-xs text-gray-400 block mb-1">API Key</label>
            <div className="relative">
              <input
                type={showKey ? 'text' : 'password'}
                placeholder="sk-or-v1-..."
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="w-full px-3 py-2 pr-10 bg-dark-surface border border-white/10 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-brand-500/50 font-mono"
                autoFocus
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
              >
                {showKey ? <FiX size={16} /> : <FiInfo size={16} />}
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Get your API key at{' '}
              <a href="https://openrouter.ai/keys" target="_blank" rel="noopener" className="text-purple-400 hover:underline">
                openrouter.ai/keys
              </a>
            </p>
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-5">
          <button
            onClick={onClose}
            className="ta-btn ta-btn-secondary"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="ta-btn ta-btn-primary"
          >
            <FiCheck size={14} />
            Save
          </button>
        </div>
      </motion.div>
    </div>
  )
}

// =============================================================================
// PÁGINA PRINCIPAL: Agents
// =============================================================================

export default function Agents() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const isDemo = location.pathname.startsWith('/demo-app')

  // State: View mode
  const [view, setView] = useState('playground') // 'playground' | 'list'

  // State: Agent configuration
  const [selectedModel, setSelectedModel] = useState('openai/gpt-4o-mini')
  const [params, setParams] = useState({ temperature: 0.7, max_tokens: 2048, top_p: 1 })
  const [selectedTools, setSelectedTools] = useState([])
  const [functions, setFunctions] = useState([])
  const [responseFormat, setResponseFormat] = useState('text')
  const [instructions, setInstructions] = useState('')

  // State: Agents list
  const [agents, setAgents] = useState([])
  const [selectedAgent, setSelectedAgent] = useState(null)
  const [showCreateModal, setShowCreateModal] = useState(false)

  // State: Serverless models (from deployed endpoints)
  const [serverlessModels, setServerlessModels] = useState([])

  // State: Code modal
  const [showCodeModal, setShowCodeModal] = useState(false)

  // State: API Key management
  const [showApiKeyModal, setShowApiKeyModal] = useState(false)
  const [hasApiKey, setHasApiKey] = useState(false)
  const [currentApiKey, setCurrentApiKey] = useState('')

  // Check for API key on mount
  useEffect(() => {
    import('../services/openRouterApi').then(({ hasOpenRouterApiKey, getOpenRouterApiKey }) => {
      setHasApiKey(hasOpenRouterApiKey())
      setCurrentApiKey(getOpenRouterApiKey() || '')
    })
  }, [])

  const handleSaveApiKey = async (key) => {
    const { setOpenRouterApiKey, hasOpenRouterApiKey } = await import('../services/openRouterApi')
    setOpenRouterApiKey(key)
    setHasApiKey(hasOpenRouterApiKey())
    setCurrentApiKey(key)
  }

  // Load agents on mount
  useEffect(() => {
    loadAgents()
    loadServerlessModels()
  }, [])

  const loadAgents = async () => {
    // TODO: Carregar agentes do backend
    // Dados demo
    if (isDemo) {
      setAgents([
        {
          id: 'agent_demo_1',
          name: 'Assistente de Código',
          description: 'Ajuda com programação e debugging',
          config: { model: 'openai/gpt-4o', tools: ['code'], instructions: 'Você é um assistente de programação.' },
          created_at: new Date().toISOString()
        },
        {
          id: 'agent_demo_2',
          name: 'Pesquisador',
          description: 'Busca informações na web',
          config: { model: 'anthropic/claude-3.5-sonnet', tools: ['search'], instructions: 'Você pesquisa informações.' },
          created_at: new Date(Date.now() - 86400000).toISOString()
        }
      ])
    }
  }

  const loadServerlessModels = async () => {
    // TODO: Carregar modelos deployados do Serverless
    setServerlessModels([
      { id: 'serverless/llama-3.1-8b', name: 'Llama 3.1 8B (Seu)', provider: 'Serverless' },
      { id: 'serverless/codellama-13b', name: 'CodeLlama 13B (Seu)', provider: 'Serverless' }
    ])
  }

  const toggleTool = (toolId) => {
    setSelectedTools(prev =>
      prev.includes(toolId)
        ? prev.filter(t => t !== toolId)
        : [...prev, toolId]
    )
  }

  const addFunction = (func) => {
    setFunctions(prev => [...prev, func])
  }

  const removeFunction = (idx) => {
    setFunctions(prev => prev.filter((_, i) => i !== idx))
  }

  const createAgent = async (agentData) => {
    const newAgent = {
      id: `agent_${Date.now()}`,
      ...agentData,
      created_at: new Date().toISOString()
    }
    setAgents(prev => [newAgent, ...prev])
    // TODO: Salvar no backend
  }

  const deleteAgent = async (agentId) => {
    if (!confirm('Are you sure you want to delete this agent?')) return
    setAgents(prev => prev.filter(a => a.id !== agentId))
    if (selectedAgent?.id === agentId) {
      setSelectedAgent(null)
    }
    // TODO: Deletar no backend
  }

  const selectAgent = (agent) => {
    setSelectedAgent(agent)
    // Carregar configuração do agente
    if (agent.config) {
      setSelectedModel(agent.config.model || 'openai/gpt-4o-mini')
      setSelectedTools(agent.config.tools || [])
      setInstructions(agent.config.instructions || '')
      setParams(agent.config.params || { temperature: 0.7, max_tokens: 2048, top_p: 1 })
      setFunctions(agent.config.functions || [])
      setResponseFormat(agent.config.responseFormat || 'text')
    }
  }

  const currentAgentConfig = {
    model: selectedModel,
    params,
    tools: selectedTools,
    functions,
    responseFormat,
    instructions
  }

  return (
    <div className="page-container">
      {/* Page Header - TailAdmin Style */}
      <div className="page-header">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500/20 to-purple-600/10 flex items-center justify-center border border-purple-500/20">
              <FiCpu className="w-6 h-6 text-purple-400" />
            </div>
            <div className="flex flex-col justify-center">
              <h1 className="page-title leading-tight">Agents</h1>
              <p className="page-subtitle mt-0.5">AI assistants specialized for specific tasks</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* View Toggle */}
            <div className="flex items-center bg-white/5 rounded-lg p-1">
              <button
                onClick={() => setView('playground')}
                className={`filter-tab ${view === 'playground' ? 'filter-tab-active' : ''}`}
              >
                <FiPlay className="inline mr-1.5" size={14} />
                Playground
              </button>
              <button
                onClick={() => setView('list')}
                className={`filter-tab ${view === 'list' ? 'filter-tab-active' : ''}`}
              >
                <FiCpu className="inline mr-1.5" size={14} />
                My Agents
              </button>
            </div>

            {view === 'playground' && (
              <>
                <button
                  onClick={() => setShowApiKeyModal(true)}
                  className={`flex items-center gap-2 px-4 py-2 border rounded-lg text-sm transition-all ${
                    hasApiKey
                      ? 'bg-green-500/10 border-green-500/30 text-green-400 hover:bg-green-500/20'
                      : 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400 hover:bg-yellow-500/20'
                  }`}
                >
                  <FiSettings size={14} />
                  {hasApiKey ? 'API Key ✓' : 'Add API Key'}
                </button>
                <button
                  onClick={() => setShowCodeModal(true)}
                  className="ta-btn ta-btn-secondary"
                >
                  <FiTerminal size={14} />
                  Code
                </button>
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="ta-btn ta-btn-primary"
                >
                  <FiPlus size={16} />
                  Create Agent
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      {view === 'list' ? (
        /* Agents List View */
        <div className="ta-card">
          <div className="ta-card-body">
            <AgentsList
              agents={agents}
              onSelect={selectAgent}
              onDelete={deleteAgent}
              selectedAgentId={selectedAgent?.id}
            />
          </div>
        </div>
      ) : (
        /* Playground View */
        <div className="grid grid-cols-1 lg:grid-cols-[400px,1fr] gap-6 h-[calc(100vh-200px)]">
          {/* Left: Configuration Panel */}
          <div className="ta-card overflow-y-auto">
            <div className="ta-card-body">
              <div className="space-y-6">
                {/* Model */}
                <div>
                  <div className="flex items-center gap-2 text-sm text-gray-400 mb-2">
                    <FiCpu size={14} />
                    <span>Model</span>
                    <InfoTooltip text="Select the AI model to power your agent" />
                  </div>
                  <ModelSelector
                    selectedModel={selectedModel}
                    onSelect={setSelectedModel}
                    serverlessModels={serverlessModels}
                  />
                  <div className="mt-2">
                    <ParametersPanel params={params} onChange={setParams} />
                  </div>
                </div>

                {/* Tools */}
                <div>
                  <div className="flex items-center gap-2 text-sm text-gray-400 mb-2">
                    <FiZap size={14} />
                    <span>Tools</span>
                    <InfoTooltip text="Enable capabilities like code execution, image generation, and web search" />
                  </div>
                  <ToolsSelector selectedTools={selectedTools} onToggle={toggleTool} />
                </div>

                {/* Functions */}
                <div>
                  <div className="flex items-center gap-2 text-sm text-gray-400 mb-2">
                    <FiCode size={14} />
                    <span>Functions</span>
                    <InfoTooltip text="Define custom functions the model can call with JSON Schema" />
                  </div>
                  <FunctionsEditor
                    functions={functions}
                    onAdd={addFunction}
                    onRemove={removeFunction}
                  />
                </div>

                {/* Response Format */}
                <div>
                  <div className="flex items-center gap-2 text-sm text-gray-400 mb-2">
                    <FiFileText size={14} />
                    <span>Response Format</span>
                    <InfoTooltip text="Choose between free-form text or structured JSON responses" />
                  </div>
                  <ResponseFormatSelector format={responseFormat} onChange={setResponseFormat} />
                </div>

                {/* Instructions */}
                <div>
                  <div className="flex items-center gap-2 text-sm text-gray-400 mb-2">
                    <FiEdit3 size={14} />
                    <span>Instructions</span>
                    <InfoTooltip text="System prompt to define the agent's behavior and personality" />
                  </div>
                  <textarea
                    value={instructions}
                    onChange={(e) => setInstructions(e.target.value)}
                    placeholder="Describe desired model behavior (tone, tool usage, response style)..."
                    rows={4}
                    className="w-full px-3 py-2 bg-dark-surface border border-white/10 rounded-lg text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-brand-500/50 resize-none"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Right: Chat Playground */}
          <div className="ta-card overflow-hidden">
            <ChatPlayground
              agentConfig={currentAgentConfig}
              disabled={!selectedModel}
              hasApiKey={hasApiKey}
              onNeedApiKey={() => setShowApiKeyModal(true)}
            />
          </div>
        </div>
      )}

      {/* Create Agent Modal */}
      <CreateAgentModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreate={createAgent}
        agentConfig={currentAgentConfig}
      />

      {/* Code Modal */}
      <CodeModal
        isOpen={showCodeModal}
        onClose={() => setShowCodeModal(false)}
        agentConfig={currentAgentConfig}
      />

      {/* API Key Modal */}
      <ApiKeyModal
        isOpen={showApiKeyModal}
        onClose={() => setShowApiKeyModal(false)}
        currentKey={currentApiKey}
        onSave={handleSaveApiKey}
      />
    </div>
  )
}
