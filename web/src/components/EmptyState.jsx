import { Search, Server, Inbox, FileQuestion, Database, FolderOpen } from 'lucide-react'
import { useTranslation } from 'react-i18next'

const icons = {
  search: Search,
  server: Server,
  inbox: Inbox,
  file: FileQuestion,
  database: Database,
  folder: FolderOpen,
}

export function EmptyState({
  icon = 'inbox',
  title,
  description,
  action,
  actionText,
  secondaryAction,
  secondaryActionText
}) {
  const { t } = useTranslation()
  const Icon = icons[icon] || Inbox

  return (
    <div className="empty-state flex flex-col items-center justify-center py-12 px-4">
      <div className="w-16 h-16 rounded-full bg-gray-700/30 flex items-center justify-center mb-4">
        <Icon className="w-8 h-8 text-gray-500" />
      </div>

      <h3 className="text-white font-medium text-sm mb-1">
        {title || t('components.emptyState.noItemFound')}
      </h3>

      {description && (
        <p className="text-gray-400 text-sm text-center mb-4 max-w-xs">
          {description}
        </p>
      )}

      {(action || secondaryAction) && (
        <div className="flex items-center gap-3 mt-2">
          {action && (
            <button
              onClick={action}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-green-600/20 hover:bg-green-600/30 border border-green-500/30 text-green-300 text-sm font-medium transition-all"
            >
              {actionText || t('components.emptyState.createNew')}
            </button>
          )}

          {secondaryAction && (
            <button
              onClick={secondaryAction}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-700/30 hover:bg-gray-700/50 border border-gray-600/30 text-gray-300 text-sm font-medium transition-all"
            >
              {secondaryActionText || t('common.back')}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

export default EmptyState
