import { useState, useEffect } from 'react'
import { Mail, Check, AlertCircle } from 'lucide-react'
import { useToast } from '../../components/Toast'
import { Alert, Card } from '../../components/tailadmin-ui'

const API_BASE = ''

// Email frequency options
const FREQUENCY_OPTIONS = [
  { value: 'weekly', label: 'Semanal', description: 'Receba um relatório toda segunda-feira' },
  { value: 'monthly', label: 'Mensal', description: 'Receba um relatório no primeiro dia de cada mês' },
  { value: 'none', label: 'Desativado', description: 'Não receber relatórios por email' },
]

export default function EmailPreferences() {
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [preferences, setPreferences] = useState({
    frequency: 'weekly',
    unsubscribed: false,
  })
  const [message, setMessage] = useState(null)

  useEffect(() => {
    loadPreferences()
  }, [])

  const loadPreferences = async () => {
    try {
      const token = localStorage.getItem('auth_token')
      const res = await fetch(`${API_BASE}/api/v1/email-preferences`, {
        credentials: 'include',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      })
      const data = await res.json()
      if (data.preferences) {
        setPreferences(data.preferences)
      }
    } catch (e) {
      // If API doesn't exist yet, use defaults
    }
    setLoading(false)
  }

  const handleFrequencyChange = (e) => {
    const newFrequency = e.target.value
    setPreferences(prev => ({
      ...prev,
      frequency: newFrequency,
      unsubscribed: newFrequency === 'none'
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setMessage(null)

    try {
      const token = localStorage.getItem('auth_token')
      const res = await fetch(`${API_BASE}/api/v1/email-preferences`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify(preferences),
        credentials: 'include'
      })
      const data = await res.json()

      if (data.success) {
        toast.success('Preferências de email salvas!')
        setMessage({ type: 'success', text: 'Preferências salvas com sucesso' })
      } else {
        toast.error(data.error || 'Falha ao salvar preferências')
        setMessage({ type: 'error', text: data.error || 'Falha ao salvar preferências' })
      }
    } catch (e) {
      toast.error('Erro de conexão')
      setMessage({ type: 'error', text: 'Erro de conexão' })
    }
    setSaving(false)
  }

  if (loading) {
    return (
      <div className="page-container">
        <div className="flex items-center justify-center py-20">
          <div className="ta-spinner" />
        </div>
      </div>
    )
  }

  return (
    <div className="page-container">
      {/* Page Header - TailAdmin Style */}
      <div className="page-header">
        <h1 className="page-title">Preferências de Email</h1>
        <p className="page-subtitle">Configure seus relatórios semanais de uso de GPU</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6 max-w-2xl">
        {message && (
          <Alert variant={message.type === 'success' ? 'success' : 'error'}>
            {message.text}
          </Alert>
        )}

        {/* Email Reports Configuration */}
        <Card
          className="border-white/10 bg-dark-surface-card"
          header={
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-brand-500/10">
                <Mail className="w-5 h-5 text-brand-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">Relatórios por Email</h3>
                <p className="text-gray-500 text-sm mt-1">Receba resumos de uso, custos e economia vs AWS</p>
              </div>
            </div>
          }
        >
          <div className="space-y-6">
            {/* Frequency Dropdown */}
            <div className="form-group">
              <label className="form-label text-gray-300 block mb-2">Frequência de Envio</label>
              <select
                name="frequency"
                className="form-input w-full"
                value={preferences.frequency}
                onChange={handleFrequencyChange}
                style={{ cursor: 'pointer' }}
              >
                {FREQUENCY_OPTIONS.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label} - {option.description}
                  </option>
                ))}
              </select>
              <small className="text-gray-500 text-xs mt-2 block">
                Os relatórios incluem: horas de GPU utilizadas, custo total, economia vs AWS e recomendações de otimização
              </small>
            </div>

            {/* Preview Info */}
            {preferences.frequency !== 'none' && (
              <div className="p-4 bg-brand-500/10 border border-brand-500/20 rounded-lg">
                <div className="flex items-start gap-3">
                  <Mail className="w-5 h-5 text-brand-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <h4 className="text-brand-300 font-medium text-sm">O que você vai receber:</h4>
                    <ul className="mt-2 space-y-1 text-gray-400 text-sm">
                      <li>• Resumo de horas de GPU utilizadas no período</li>
                      <li>• Custo total e comparação com semana/mês anterior</li>
                      <li>• Economia calculada vs preços AWS equivalentes</li>
                      <li>• Recomendações personalizadas do AI Wizard</li>
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* Unsubscribed Warning */}
            {preferences.frequency === 'none' && (
              <div className="p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-yellow-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <h4 className="text-yellow-300 font-medium text-sm">Relatórios desativados</h4>
                    <p className="mt-1 text-gray-400 text-sm">
                      Você não receberá relatórios por email. Você pode reativar a qualquer momento.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </Card>

        {/* Save Button */}
        <div className="flex flex-col sm:flex-row gap-3 pt-4">
          <button
            type="submit"
            disabled={saving}
            className="flex-1 py-3 px-4 rounded-lg font-semibold transition-all flex items-center justify-center gap-2 bg-brand-800/30 hover:bg-brand-800/50 border border-brand-700/40 text-brand-400 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? (
              <>
                <span className="spinner" />
                Salvando...
              </>
            ) : (
              <>
                <Check className="w-4 h-4" />
                Salvar Preferências
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  )
}
