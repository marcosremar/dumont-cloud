import React, { useState, useEffect, useRef } from 'react'
import {
    Send,
    RefreshCw,
    ChevronDown,
    Clock,
    Activity,
    Trash2,
    Server,
    Cpu,
    Zap
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'react-markdown'

// NOTE: Models must be deployed on remote GPUs (VAST.ai), not local machine
// Use the Deploy Wizard to provision a GPU with Ollama or vLLM first

export default function Playground() {
    const [models, setModels] = useState([])
    const [selectedModel, setSelectedModel] = useState(null)
    const [messages, setMessages] = useState([])
    const [inputText, setInputText] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [refreshing, setRefreshing] = useState(false)
    const [showModelSelector, setShowModelSelector] = useState(false)
    const messagesEndRef = useRef(null)
    const modelSelectorRef = useRef(null)

    // Fetch available models from API (remote GPUs only)
    const fetchModels = async () => {
        setRefreshing(true)
        try {
            const token = localStorage.getItem('auth_token')
            const headers = token ? { Authorization: `Bearer ${token}` } : {}
            const res = await fetch('/api/v1/chat/models', { headers })
            const data = await res.json()
            if (data.models && data.models.length > 0) {
                setModels(data.models)
                // Auto-select first model if none selected
                if (!selectedModel) {
                    setSelectedModel(data.models[0])
                }
            } else {
                setModels([])
            }
        } catch (err) {
            console.error('Failed to fetch models:', err)
            setModels([])
        } finally {
            setRefreshing(false)
        }
    }

    useEffect(() => {
        fetchModels()
        const interval = setInterval(fetchModels, 30000)
        return () => clearInterval(interval)
    }, [])

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    useEffect(() => {
        const handleClickOutside = (e) => {
            if (modelSelectorRef.current && !modelSelectorRef.current.contains(e.target)) {
                setShowModelSelector(false)
            }
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [])

    // Helper: fetch with timeout
    const fetchWithTimeout = async (url, options = {}, timeoutMs = 60000) => {
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs)

        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            })
            clearTimeout(timeoutId)
            return response
        } catch (error) {
            clearTimeout(timeoutId)
            if (error.name === 'AbortError') {
                throw new Error(`Timeout: servidor demorou mais de ${timeoutMs/1000}s`)
            }
            throw error
        }
    }

    // Check model health
    const checkModelHealth = async (model) => {
        try {
            if (model.runtime === 'vllm' || model.api_format === 'openai') {
                const proxyUrl = `/api/v1/chat/proxy/${model.id}/vllm/models`
                const res = await fetchWithTimeout(proxyUrl, {}, 10000)
                if (!res.ok) return { healthy: false, error: 'vLLM não respondeu' }
                const data = await res.json()
                const modelList = data.data || []
                if (modelList.length === 0) {
                    return { healthy: false, error: 'Nenhum modelo carregado', models: [] }
                }
                return { healthy: true, models: modelList.map(m => ({ name: m.id })), isVLLM: true }
            }

            const proxyUrl = `/api/v1/chat/proxy/${model.id}/tags`
            const res = await fetchWithTimeout(proxyUrl, {}, 10000)
            if (!res.ok) return { healthy: false, error: 'Ollama não respondeu' }
            const data = await res.json()
            if (!data.models || data.models.length === 0) {
                return { healthy: false, error: 'Nenhum modelo instalado', models: [] }
            }
            return { healthy: true, models: data.models, isVLLM: false }
        } catch (e) {
            return { healthy: false, error: e.message }
        }
    }

    const sendMessage = async () => {
        if (!inputText.trim() || !selectedModel || isLoading) return

        const userMsg = { role: 'user', content: inputText, id: Date.now() }
        setMessages(prev => [...prev, userMsg])
        setInputText('')
        setIsLoading(true)

        const startTime = Date.now()

        try {
            const health = await checkModelHealth(selectedModel)
            if (!health.healthy) {
                throw new Error(health.error || 'Modelo offline')
            }

            const modelName = health.models[0]?.name || 'default'
            const messageHistory = messages.map(m => ({ role: m.role, content: m.content }))

            let proxyUrl, requestBody

            if (health.isVLLM || selectedModel.runtime === 'vllm' || selectedModel.api_format === 'openai') {
                proxyUrl = `/api/v1/chat/proxy/${selectedModel.id}/vllm/chat`
                requestBody = {
                    model: modelName,
                    messages: [...messageHistory, { role: 'user', content: userMsg.content }],
                    stream: false,
                    max_tokens: 2048,
                    temperature: 0.7
                }
            } else {
                proxyUrl = `/api/v1/chat/proxy/${selectedModel.id}/chat`
                requestBody = {
                    model: modelName,
                    messages: [...messageHistory, { role: 'user', content: userMsg.content }],
                    stream: false
                }
            }

            const response = await fetchWithTimeout(
                proxyUrl,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(requestBody)
                },
                120000
            )

            if (!response.ok) {
                const errorText = await response.text().catch(() => response.statusText)
                throw new Error(`Erro ${response.status}: ${errorText}`)
            }

            const data = await response.json()
            const responseTime = Date.now() - startTime

            let content
            if (data.choices && data.choices[0]?.message?.content) {
                content = data.choices[0].message.content
            } else {
                content = data.message?.content || data.response || 'Sem resposta'
            }

            const totalTokens = data.usage?.total_tokens || Math.ceil(content.split(/\s+/).length * 1.3)
            const tokensPerSecond = totalTokens / (responseTime / 1000)

            setMessages(prev => [...prev, {
                role: 'assistant',
                content,
                id: Date.now() + Math.random(),
                stats: {
                    responseTime,
                    totalTokens,
                    tokensPerSecond,
                    modelUsed: modelName,
                    runtime: health.isVLLM ? 'vLLM' : 'Ollama'
                }
            }])
        } catch (error) {
            setMessages(prev => [...prev, {
                role: 'system',
                content: `Error: ${error.message}`,
                isError: true,
                id: Date.now() + Math.random()
            }])
        } finally {
            setIsLoading(false)
        }
    }

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            sendMessage()
        }
    }

    const clearMessages = () => {
        setMessages([])
    }

    const getModelDisplayName = (model) => {
        if (!model) return 'Select Model'
        return model.label || model.name || model.gpu || `GPU ${model.id}`
    }

    const getRuntimeBadge = (model) => {
        if (!model) return null
        if (model.runtime === 'vllm' || model.api_format === 'openai') {
            return <span className="text-xs text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full">vLLM</span>
        }
        return <span className="text-xs text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded-full">Ollama</span>
    }

    return (
        <div className="flex flex-col h-[calc(100vh-6rem)]">
            {/* Main Content */}
            <div className="flex-1 flex flex-col max-w-4xl mx-auto w-full px-4 py-6">

                {/* Empty State - When no messages */}
                {messages.length === 0 && (
                    <div className="flex-1 flex flex-col items-center justify-center">
                        <div className="text-center mb-8">
                            <p className="text-2xl font-medium text-gray-300 mb-2">Start a conversation</p>
                            <p className="text-gray-500">
                                Ask me anything and I'll respond using {getModelDisplayName(selectedModel)}
                            </p>
                        </div>

                        {/* Model Selector */}
                        <div className="relative mb-6" ref={modelSelectorRef}>
                            <button
                                onClick={() => setShowModelSelector(!showModelSelector)}
                                className="flex items-center gap-3 px-4 py-3 bg-[#1c2128] border border-white/10 rounded-xl hover:border-white/20 transition-all min-w-[280px]"
                            >
                                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                                    <Cpu className="w-4 h-4 text-white" />
                                </div>
                                <div className="flex-1 text-left">
                                    <span className="text-gray-200 font-medium">{getModelDisplayName(selectedModel)}</span>
                                </div>
                                {selectedModel && getRuntimeBadge(selectedModel)}
                                <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform ${showModelSelector ? 'rotate-180' : ''}`} />
                            </button>

                            <AnimatePresence>
                                {showModelSelector && (
                                    <motion.div
                                        initial={{ opacity: 0, y: -10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0, y: -10 }}
                                        className="absolute left-0 right-0 top-full mt-2 bg-[#1c2128] border border-white/10 rounded-xl shadow-2xl z-50 overflow-hidden"
                                    >
                                        <div className="p-3 border-b border-white/5 flex items-center justify-between">
                                            <span className="text-sm font-medium text-gray-400">Available Models</span>
                                            <button
                                                onClick={(e) => { e.stopPropagation(); fetchModels(); }}
                                                className={`p-1.5 rounded-lg hover:bg-white/5 transition-all ${refreshing ? 'animate-spin' : ''}`}
                                            >
                                                <RefreshCw className="w-4 h-4 text-gray-400" />
                                            </button>
                                        </div>
                                        <div className="max-h-64 overflow-y-auto p-2">
                                            {models.length === 0 ? (
                                                <div className="text-center py-8 text-gray-500">
                                                    <Server className="w-8 h-8 mx-auto mb-3 opacity-50" />
                                                    <p className="text-sm font-medium">No models available</p>
                                                    <p className="text-xs mt-1">Deploy a model from the Models page</p>
                                                </div>
                                            ) : (
                                                models.map(model => (
                                                    <button
                                                        key={model.id}
                                                        onClick={() => { setSelectedModel(model); setShowModelSelector(false); }}
                                                        className={`w-full flex items-center gap-3 p-3 rounded-lg transition-all ${
                                                            selectedModel?.id === model.id
                                                                ? 'bg-purple-500/10 border border-purple-500/30'
                                                                : 'hover:bg-white/5'
                                                        }`}
                                                    >
                                                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500/20 to-pink-500/20 flex items-center justify-center">
                                                            <Zap className="w-4 h-4 text-purple-400" />
                                                        </div>
                                                        <div className="flex-1 text-left">
                                                            <p className="text-sm font-medium text-gray-200">{getModelDisplayName(model)}</p>
                                                            <p className="text-xs text-gray-500">{model.gpu || model.ip}</p>
                                                        </div>
                                                        {getRuntimeBadge(model)}
                                                        <span className="w-2 h-2 rounded-full bg-green-500" />
                                                    </button>
                                                ))
                                            )}
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>

                        {/* Input Area for Empty State */}
                        <div className="w-full max-w-2xl">
                            <div className="relative">
                                <input
                                    type="text"
                                    value={inputText}
                                    onChange={(e) => setInputText(e.target.value)}
                                    onKeyDown={handleKeyDown}
                                    placeholder={`Ask ${getModelDisplayName(selectedModel)} anything...`}
                                    disabled={!selectedModel || isLoading}
                                    className="w-full bg-[#1c2128] border border-white/10 rounded-xl px-5 py-4 pr-14 text-gray-200 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50 transition-all placeholder-gray-500"
                                />
                                <button
                                    onClick={sendMessage}
                                    disabled={!selectedModel || isLoading || !inputText.trim()}
                                    className="absolute right-2 top-1/2 -translate-y-1/2 p-3 rounded-lg bg-purple-600 text-white hover:bg-purple-500 disabled:opacity-50 disabled:hover:bg-purple-600 transition-all"
                                >
                                    <Send className="w-5 h-5" />
                                </button>
                            </div>
                            <p className="text-xs text-gray-500 mt-3 text-center">
                                This app is running on your deployed GPU for best performance
                            </p>
                        </div>
                    </div>
                )}

                {/* Chat View - When there are messages */}
                {messages.length > 0 && (
                    <>
                        {/* Header with model selector */}
                        <div className="flex items-center justify-between mb-4">
                            <div className="relative" ref={messages.length > 0 ? modelSelectorRef : null}>
                                <button
                                    onClick={() => setShowModelSelector(!showModelSelector)}
                                    className="flex items-center gap-2 px-3 py-2 bg-[#1c2128] border border-white/10 rounded-lg hover:border-white/20 transition-all"
                                >
                                    <div className="w-6 h-6 rounded bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                                        <Cpu className="w-3 h-3 text-white" />
                                    </div>
                                    <span className="text-sm text-gray-300">{getModelDisplayName(selectedModel)}</span>
                                    {selectedModel && getRuntimeBadge(selectedModel)}
                                    <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${showModelSelector ? 'rotate-180' : ''}`} />
                                </button>

                                <AnimatePresence>
                                    {showModelSelector && (
                                        <motion.div
                                            initial={{ opacity: 0, y: -10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            exit={{ opacity: 0, y: -10 }}
                                            className="absolute left-0 top-full mt-2 w-72 bg-[#1c2128] border border-white/10 rounded-xl shadow-2xl z-50 overflow-hidden"
                                        >
                                            <div className="max-h-64 overflow-y-auto p-2">
                                                {models.map(model => (
                                                    <button
                                                        key={model.id}
                                                        onClick={() => { setSelectedModel(model); setShowModelSelector(false); }}
                                                        className={`w-full flex items-center gap-3 p-3 rounded-lg transition-all ${
                                                            selectedModel?.id === model.id
                                                                ? 'bg-purple-500/10'
                                                                : 'hover:bg-white/5'
                                                        }`}
                                                    >
                                                        <Zap className="w-4 h-4 text-purple-400" />
                                                        <span className="text-sm text-gray-200">{getModelDisplayName(model)}</span>
                                                        {getRuntimeBadge(model)}
                                                    </button>
                                                ))}
                                            </div>
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </div>

                            <button
                                onClick={clearMessages}
                                className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all"
                                title="Clear chat"
                            >
                                <Trash2 className="w-4 h-4" />
                            </button>
                        </div>

                        {/* Messages */}
                        <div className="flex-1 overflow-y-auto space-y-4 mb-4">
                            {messages.map((msg, idx) => (
                                <motion.div
                                    key={msg.id || idx}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                                >
                                    <div
                                        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                                            msg.role === 'user'
                                                ? 'bg-purple-600 text-white'
                                                : msg.isError
                                                    ? 'bg-red-500/10 border border-red-500/30 text-red-300'
                                                    : 'bg-[#1c2128] border border-white/5 text-gray-200'
                                        }`}
                                    >
                                        <div className="prose prose-invert prose-sm max-w-none">
                                            <ReactMarkdown>{msg.content}</ReactMarkdown>
                                        </div>

                                        {msg.stats && (
                                            <div className="flex items-center gap-3 mt-2 pt-2 border-t border-white/10 text-xs text-gray-500">
                                                <span className="flex items-center gap-1">
                                                    <Activity className="w-3 h-3" />
                                                    {msg.stats.tokensPerSecond?.toFixed(1)} tok/s
                                                </span>
                                                <span className="flex items-center gap-1">
                                                    <Clock className="w-3 h-3" />
                                                    {(msg.stats.responseTime / 1000).toFixed(2)}s
                                                </span>
                                                <span className="text-gray-600">
                                                    {msg.stats.runtime}
                                                </span>
                                            </div>
                                        )}
                                    </div>
                                </motion.div>
                            ))}

                            {isLoading && (
                                <div className="flex justify-start">
                                    <div className="bg-[#1c2128] border border-white/5 rounded-2xl px-4 py-3">
                                        <div className="flex gap-1">
                                            <span className="w-2 h-2 rounded-full bg-purple-500 animate-bounce" />
                                            <span className="w-2 h-2 rounded-full bg-purple-500 animate-bounce" style={{ animationDelay: '0.1s' }} />
                                            <span className="w-2 h-2 rounded-full bg-purple-500 animate-bounce" style={{ animationDelay: '0.2s' }} />
                                        </div>
                                    </div>
                                </div>
                            )}
                            <div ref={messagesEndRef} />
                        </div>

                        {/* Input Area */}
                        <div className="relative">
                            <input
                                type="text"
                                value={inputText}
                                onChange={(e) => setInputText(e.target.value)}
                                onKeyDown={handleKeyDown}
                                placeholder={`Ask ${getModelDisplayName(selectedModel)} anything...`}
                                disabled={!selectedModel || isLoading}
                                className="w-full bg-[#1c2128] border border-white/10 rounded-xl px-5 py-4 pr-14 text-gray-200 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50 transition-all placeholder-gray-500"
                            />
                            <button
                                onClick={sendMessage}
                                disabled={!selectedModel || isLoading || !inputText.trim()}
                                className="absolute right-2 top-1/2 -translate-y-1/2 p-3 rounded-lg bg-purple-600 text-white hover:bg-purple-500 disabled:opacity-50 disabled:hover:bg-purple-600 transition-all"
                            >
                                <Send className="w-5 h-5" />
                            </button>
                        </div>
                    </>
                )}
            </div>
        </div>
    )
}
