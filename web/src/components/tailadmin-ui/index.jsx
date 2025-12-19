import { ChevronRight, TrendingUp, TrendingDown, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

// Page Header with Breadcrumb
export function PageHeader({ title, subtitle, breadcrumbs = [], actions }) {
  return (
    <div className="mb-6">
      {breadcrumbs.length > 0 && (
        <nav className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 mb-3">
          {breadcrumbs.map((item, index) => (
            <span key={index} className="flex items-center gap-2">
              {index > 0 && <ChevronRight size={14} className="text-gray-300 dark:text-gray-600" />}
              {item.href ? (
                <Link to={item.href} className="hover:text-brand-500 transition-colors">
                  {item.label}
                </Link>
              ) : (
                <span className="text-gray-900 dark:text-white font-medium">{item.label}</span>
              )}
            </span>
          ))}
        </nav>
      )}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">{title}</h1>
          {subtitle && <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{subtitle}</p>}
        </div>
        {actions && <div className="flex items-center gap-3">{actions}</div>}
      </div>
    </div>
  );
}

// Stat Card
export function StatCard({
  title,
  value,
  change,
  changeType = 'up',
  icon: Icon,
  iconColor = 'primary',
  subtitle,
  onClick
}) {
  const iconColorClasses = {
    primary: 'bg-brand-50 text-brand-500 dark:bg-brand-500/10 dark:text-brand-400',
    success: 'bg-success-50 text-success-500 dark:bg-success-500/10 dark:text-success-400',
    warning: 'bg-warning-50 text-warning-500 dark:bg-warning-500/10 dark:text-warning-400',
    error: 'bg-error-50 text-error-500 dark:bg-error-500/10 dark:text-error-400',
    gray: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400',
  };

  return (
    <div
      className={`bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 shadow-theme-sm ${onClick ? 'cursor-pointer hover:border-brand-300 dark:hover:border-brand-700 transition-colors' : ''}`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">{title}</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
          {subtitle && <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">{subtitle}</p>}
          {change && (
            <div className={`flex items-center gap-1 mt-2 text-xs font-medium ${changeType === 'up' ? 'text-success-500' : 'text-error-500'}`}>
              {changeType === 'up' ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
              <span>{change}</span>
            </div>
          )}
        </div>
        {Icon && (
          <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${iconColorClasses[iconColor]}`}>
            <Icon size={24} />
          </div>
        )}
      </div>
    </div>
  );
}

// Card Component
export function Card({ children, className = '', header, footer, noPadding = false }) {
  return (
    <div className={`bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-theme-sm ${className}`}>
      {header && (
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800">
          {typeof header === 'string' ? (
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{header}</h3>
          ) : header}
        </div>
      )}
      <div className={noPadding ? '' : 'p-6'}>{children}</div>
      {footer && (
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50 rounded-b-xl">
          {footer}
        </div>
      )}
    </div>
  );
}

// Button Component
export function Button({
  children,
  variant = 'primary',
  size = 'md',
  icon: Icon,
  iconPosition = 'left',
  loading = false,
  disabled = false,
  className = '',
  ...props
}) {
  const variants = {
    primary: 'bg-brand-500 text-white hover:bg-brand-600 focus:ring-brand-500',
    secondary: 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700',
    success: 'bg-success-500 text-white hover:bg-success-600 focus:ring-success-500',
    error: 'bg-error-500 text-white hover:bg-error-600 focus:ring-error-500',
    warning: 'bg-warning-500 text-white hover:bg-warning-600 focus:ring-warning-500',
    outline: 'border border-gray-300 bg-transparent text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800',
    ghost: 'bg-transparent text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800',
  };

  const sizes = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2.5 text-sm',
    lg: 'px-6 py-3 text-base',
  };

  return (
    <button
      className={`inline-flex items-center justify-center gap-2 font-medium rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed ${variants[variant]} ${sizes[size]} ${className}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading && (
        <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
      )}
      {Icon && iconPosition === 'left' && !loading && <Icon size={size === 'sm' ? 14 : size === 'lg' ? 20 : 16} />}
      {children}
      {Icon && iconPosition === 'right' && !loading && <Icon size={size === 'sm' ? 14 : size === 'lg' ? 20 : 16} />}
    </button>
  );
}

// Badge Component
export function Badge({ children, variant = 'gray', size = 'md', dot = false }) {
  const variants = {
    primary: 'bg-brand-50 text-brand-700 dark:bg-brand-500/10 dark:text-brand-400',
    success: 'bg-success-50 text-success-700 dark:bg-success-500/10 dark:text-success-400',
    warning: 'bg-warning-50 text-warning-700 dark:bg-warning-500/10 dark:text-warning-400',
    error: 'bg-error-50 text-error-700 dark:bg-error-500/10 dark:text-error-400',
    gray: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
  };

  const sizes = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-0.5 text-xs',
    lg: 'px-3 py-1 text-sm',
  };

  const dotColors = {
    primary: 'bg-brand-500',
    success: 'bg-success-500',
    warning: 'bg-warning-500',
    error: 'bg-error-500',
    gray: 'bg-gray-500',
  };

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full font-medium ${variants[variant]} ${sizes[size]}`}>
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${dotColors[variant]}`} />}
      {children}
    </span>
  );
}

// Table Component
export function Table({ columns, data, onRowClick, emptyMessage = 'Nenhum dado encontrado' }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead className="bg-gray-50 dark:bg-gray-800">
          <tr>
            {columns.map((col, i) => (
              <th
                key={i}
                className={`px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider ${col.className || ''}`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-12 text-center text-gray-500 dark:text-gray-400">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, rowIndex) => (
              <tr
                key={rowIndex}
                className={`border-b border-gray-200 dark:border-gray-800 ${onRowClick ? 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50' : ''} transition-colors`}
                onClick={() => onRowClick?.(row)}
              >
                {columns.map((col, colIndex) => (
                  <td key={colIndex} className={`px-4 py-4 text-sm text-gray-900 dark:text-gray-100 ${col.cellClassName || ''}`}>
                    {col.render ? col.render(row[col.accessor], row) : row[col.accessor]}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

// Input Component
export function Input({ label, error, helper, className = '', ...props }) {
  return (
    <div className={className}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
          {label}
        </label>
      )}
      <input
        className={`w-full px-4 py-2.5 text-sm text-gray-900 bg-white border rounded-lg focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 dark:bg-gray-900 dark:border-gray-700 dark:text-white dark:focus:border-brand-400 transition-colors ${error ? 'border-error-500' : 'border-gray-300'}`}
        {...props}
      />
      {(error || helper) && (
        <p className={`mt-1.5 text-xs ${error ? 'text-error-500' : 'text-gray-500 dark:text-gray-400'}`}>
          {error || helper}
        </p>
      )}
    </div>
  );
}

// Select Component
export function Select({ label, error, helper, options = [], className = '', ...props }) {
  return (
    <div className={className}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
          {label}
        </label>
      )}
      <select
        className={`w-full px-4 py-2.5 text-sm text-gray-900 bg-white border rounded-lg focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 dark:bg-gray-900 dark:border-gray-700 dark:text-white cursor-pointer ${error ? 'border-error-500' : 'border-gray-300'}`}
        {...props}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
      {(error || helper) && (
        <p className={`mt-1.5 text-xs ${error ? 'text-error-500' : 'text-gray-500 dark:text-gray-400'}`}>
          {error || helper}
        </p>
      )}
    </div>
  );
}

// Alert Component
export function Alert({ variant = 'info', title, children, icon: Icon, onClose }) {
  const variants = {
    info: 'bg-brand-50 text-brand-800 dark:bg-brand-500/10 dark:text-brand-300 border-brand-200 dark:border-brand-800',
    success: 'bg-success-50 text-success-800 dark:bg-success-500/10 dark:text-success-300 border-success-200 dark:border-success-800',
    warning: 'bg-warning-50 text-warning-800 dark:bg-warning-500/10 dark:text-warning-300 border-warning-200 dark:border-warning-800',
    error: 'bg-error-50 text-error-800 dark:bg-error-500/10 dark:text-error-300 border-error-200 dark:border-error-800',
  };

  return (
    <div className={`p-4 rounded-lg border ${variants[variant]} flex items-start gap-3`}>
      {Icon && <Icon size={20} className="flex-shrink-0 mt-0.5" />}
      <div className="flex-1">
        {title && <p className="font-medium mb-1">{title}</p>}
        <div className="text-sm opacity-90">{children}</div>
      </div>
      {onClose && (
        <button onClick={onClose} className="flex-shrink-0 hover:opacity-70">
          <span className="sr-only">Fechar</span>
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </button>
      )}
    </div>
  );
}

// Progress Bar
export function Progress({ value = 0, max = 100, variant = 'primary', size = 'md', showLabel = false }) {
  const percent = Math.min(100, Math.max(0, (value / max) * 100));

  const variants = {
    primary: 'bg-brand-500',
    success: 'bg-success-500',
    warning: 'bg-warning-500',
    error: 'bg-error-500',
  };

  const sizes = {
    sm: 'h-1',
    md: 'h-2',
    lg: 'h-3',
  };

  return (
    <div className="flex items-center gap-3">
      <div className={`flex-1 bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden ${sizes[size]}`}>
        <div
          className={`h-full rounded-full transition-all duration-300 ${variants[variant]}`}
          style={{ width: `${percent}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300 min-w-[3rem] text-right">
          {Math.round(percent)}%
        </span>
      )}
    </div>
  );
}

// Empty State
export function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      {Icon && (
        <div className="w-16 h-16 text-gray-300 dark:text-gray-600 mb-4">
          <Icon size={64} />
        </div>
      )}
      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">{title}</h3>
      {description && (
        <p className="text-sm text-gray-500 dark:text-gray-400 max-w-sm mb-4">{description}</p>
      )}
      {action}
    </div>
  );
}

// Loading Spinner
export function Spinner({ size = 'md', className = '' }) {
  const sizes = {
    sm: 'w-4 h-4 border-2',
    md: 'w-8 h-8 border-4',
    lg: 'w-12 h-12 border-4',
  };

  return (
    <div className={`${sizes[size]} border-gray-200 border-t-brand-500 rounded-full animate-spin ${className}`} />
  );
}

// Grid Layouts
export function StatsGrid({ children }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {children}
    </div>
  );
}

export function CardsGrid({ children, cols = 3 }) {
  const colsClass = {
    2: 'md:grid-cols-2',
    3: 'md:grid-cols-2 xl:grid-cols-3',
    4: 'md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4',
  };

  return (
    <div className={`grid grid-cols-1 ${colsClass[cols]} gap-6`}>
      {children}
    </div>
  );
}
