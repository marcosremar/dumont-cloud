import { useTranslation } from 'react-i18next'
import { Globe } from 'lucide-react'

const AVAILABLE_LANGUAGES = [
  { code: 'en', name: 'English', flag: '🇺🇸' },
  { code: 'es', name: 'Español', flag: '🇪🇸' },
]

export function LanguageSelector({ className = '' }) {
  const { t, i18n } = useTranslation()

  const handleLanguageChange = (languageCode) => {
    i18n.changeLanguage(languageCode)
    localStorage.setItem('language', languageCode)
  }

  const currentLanguage = i18n.language || 'en'

  return (
    <div className={`space-y-3 ${className}`}>
      {AVAILABLE_LANGUAGES.map((lang) => {
        const isSelected = currentLanguage === lang.code

        return (
          <button
            key={lang.code}
            type="button"
            onClick={() => handleLanguageChange(lang.code)}
            className={`w-full flex items-center justify-between p-4 rounded-lg border transition-all ${
              isSelected
                ? 'bg-brand-500/10 border-brand-500/30 text-brand-300'
                : 'bg-white/5 border-white/10 text-gray-300 hover:bg-white/10 hover:border-white/20'
            }`}
          >
            <div className="flex items-center gap-3">
              <span className="text-xl">{lang.flag}</span>
              <div className="text-left">
                <div className="font-medium">{lang.name}</div>
                <div className="text-sm text-gray-500">{t(`languages.${lang.code}`)}</div>
              </div>
            </div>
            {isSelected && (
              <div className="w-5 h-5 rounded-full bg-brand-500 flex items-center justify-center">
                <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                </svg>
              </div>
            )}
          </button>
        )
      })}
    </div>
  )
}

export default LanguageSelector
