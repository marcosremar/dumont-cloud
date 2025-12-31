/**
 * TemplateFilters Component
 * Provides GPU VRAM filtering and category filtering for the template marketplace
 */
import { useDispatch, useSelector } from 'react-redux'
import {
  Card,
  Badge,
  Button,
  Switch,
} from '../tailadmin-ui'
import {
  Cpu,
  Filter,
  Layers,
  Check,
  RotateCcw,
  BookOpen,
  Image,
  MessageSquare,
  Server,
} from 'lucide-react'
import {
  setFilters,
  resetFilters,
  selectTemplateFilters,
} from '../../store/slices/templateSlice'

// VRAM filter options based on template GPU requirements
const VRAM_OPTIONS = [
  { value: null, label: 'All GPUs', description: 'Show all templates' },
  { value: 4, label: '4GB+', description: 'Entry-level GPUs' },
  { value: 8, label: '8GB+', description: 'Standard GPUs' },
  { value: 16, label: '16GB+', description: 'Premium GPUs' },
  { value: 24, label: '24GB+', description: 'High-end GPUs' },
]

// Category filter options matching backend categories
const CATEGORY_OPTIONS = [
  { value: null, label: 'All Categories', icon: Server, color: 'gray' },
  { value: 'notebook', label: 'Notebooks', icon: BookOpen, color: 'primary' },
  { value: 'image_generation', label: 'Image Gen', icon: Image, color: 'success' },
  { value: 'llm_inference', label: 'LLM Inference', icon: MessageSquare, color: 'warning' },
]

// Get VRAM tier badge variant
const getVramVariant = (vram) => {
  if (vram >= 24) return 'error'
  if (vram >= 16) return 'warning'
  if (vram >= 8) return 'primary'
  return 'success'
}

export function TemplateFilters({ onFilterChange, compact = false }) {
  const dispatch = useDispatch()
  const filters = useSelector(selectTemplateFilters)

  const handleVramChange = (value) => {
    dispatch(setFilters({ min_vram: value }))
    onFilterChange?.({ ...filters, min_vram: value })
  }

  const handleCategoryChange = (value) => {
    dispatch(setFilters({ category: value }))
    onFilterChange?.({ ...filters, category: value })
  }

  const handleVerifiedChange = (checked) => {
    dispatch(setFilters({ verified_only: checked }))
    onFilterChange?.({ ...filters, verified_only: checked })
  }

  const handleReset = () => {
    dispatch(resetFilters())
    onFilterChange?.({ min_vram: null, category: null, verified_only: false })
  }

  const hasActiveFilters =
    filters.min_vram !== null ||
    filters.category !== null ||
    filters.verified_only

  if (compact) {
    return (
      <div className="flex flex-wrap items-center gap-2">
        {/* VRAM Quick Filters */}
        <div className="flex items-center gap-1">
          <Cpu className="w-3.5 h-3.5 text-gray-400" />
          {VRAM_OPTIONS.map((option) => (
            <button
              key={option.value ?? 'all'}
              onClick={() => handleVramChange(option.value)}
              className={`px-2.5 py-1 text-[10px] font-medium rounded-lg transition-all ${
                filters.min_vram === option.value
                  ? 'bg-brand-500 text-white'
                  : 'bg-gray-800/50 text-gray-400 hover:bg-gray-700/50 hover:text-gray-300'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>

        {/* Category Pills */}
        <div className="flex items-center gap-1 ml-2 pl-2 border-l border-gray-700">
          <Layers className="w-3.5 h-3.5 text-gray-400" />
          {CATEGORY_OPTIONS.map((option) => {
            const Icon = option.icon
            return (
              <button
                key={option.value ?? 'all'}
                onClick={() => handleCategoryChange(option.value)}
                className={`px-2.5 py-1 text-[10px] font-medium rounded-lg transition-all flex items-center gap-1 ${
                  filters.category === option.value
                    ? 'bg-brand-500 text-white'
                    : 'bg-gray-800/50 text-gray-400 hover:bg-gray-700/50 hover:text-gray-300'
                }`}
              >
                <Icon className="w-3 h-3" />
                {option.label}
              </button>
            )
          })}
        </div>

        {/* Verified Toggle */}
        <div className="flex items-center gap-2 ml-2 pl-2 border-l border-gray-700">
          <Switch
            checked={filters.verified_only}
            onCheckedChange={handleVerifiedChange}
            label=""
            className="scale-75"
          />
          <span className="text-[10px] text-gray-400">Verified only</span>
        </div>

        {/* Reset Button */}
        {hasActiveFilters && (
          <button
            onClick={handleReset}
            className="ml-2 px-2 py-1 text-[10px] text-gray-400 hover:text-white flex items-center gap-1"
          >
            <RotateCcw className="w-3 h-3" />
            Reset
          </button>
        )}
      </div>
    )
  }

  return (
    <Card className="sticky top-4">
      <div className="p-4 border-b border-white/10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-brand-400" />
            <span className="text-sm font-semibold text-white">Filters</span>
          </div>
          {hasActiveFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleReset}
              className="text-[10px] text-gray-400 hover:text-white"
            >
              <RotateCcw className="w-3 h-3 mr-1" />
              Reset
            </Button>
          )}
        </div>
      </div>

      {/* GPU VRAM Filter */}
      <div className="p-4 border-b border-white/10">
        <div className="flex items-center gap-2 mb-3">
          <Cpu className="w-4 h-4 text-gray-400" />
          <span className="text-xs font-medium text-gray-300 uppercase tracking-wider">
            GPU VRAM
          </span>
        </div>
        <div className="space-y-1.5">
          {VRAM_OPTIONS.map((option) => (
            <button
              key={option.value ?? 'all'}
              onClick={() => handleVramChange(option.value)}
              className={`w-full flex items-center justify-between p-2.5 rounded-lg transition-all ${
                filters.min_vram === option.value
                  ? 'bg-brand-500/10 border border-brand-500/30'
                  : 'bg-gray-800/30 border border-transparent hover:bg-gray-800/50 hover:border-gray-700'
              }`}
            >
              <div className="flex items-center gap-2">
                {option.value !== null && (
                  <Badge
                    variant={getVramVariant(option.value)}
                    className="text-[9px] px-1.5"
                  >
                    {option.value}GB
                  </Badge>
                )}
                <span
                  className={`text-xs ${
                    filters.min_vram === option.value
                      ? 'text-white font-medium'
                      : 'text-gray-400'
                  }`}
                >
                  {option.label}
                </span>
              </div>
              {filters.min_vram === option.value && (
                <Check className="w-3.5 h-3.5 text-brand-400" />
              )}
            </button>
          ))}
        </div>
        <p className="mt-2 text-[10px] text-gray-500">
          Filter templates by minimum GPU VRAM requirements
        </p>
      </div>

      {/* Category Filter */}
      <div className="p-4 border-b border-white/10">
        <div className="flex items-center gap-2 mb-3">
          <Layers className="w-4 h-4 text-gray-400" />
          <span className="text-xs font-medium text-gray-300 uppercase tracking-wider">
            Category
          </span>
        </div>
        <div className="space-y-1.5">
          {CATEGORY_OPTIONS.map((option) => {
            const Icon = option.icon
            return (
              <button
                key={option.value ?? 'all'}
                onClick={() => handleCategoryChange(option.value)}
                className={`w-full flex items-center justify-between p-2.5 rounded-lg transition-all ${
                  filters.category === option.value
                    ? 'bg-brand-500/10 border border-brand-500/30'
                    : 'bg-gray-800/30 border border-transparent hover:bg-gray-800/50 hover:border-gray-700'
                }`}
              >
                <div className="flex items-center gap-2">
                  <div
                    className={`p-1 rounded ${
                      filters.category === option.value
                        ? 'bg-brand-500/20'
                        : 'bg-gray-700/50'
                    }`}
                  >
                    <Icon
                      className={`w-3.5 h-3.5 ${
                        filters.category === option.value
                          ? 'text-brand-400'
                          : 'text-gray-400'
                      }`}
                    />
                  </div>
                  <span
                    className={`text-xs ${
                      filters.category === option.value
                        ? 'text-white font-medium'
                        : 'text-gray-400'
                    }`}
                  >
                    {option.label}
                  </span>
                </div>
                {filters.category === option.value && (
                  <Check className="w-3.5 h-3.5 text-brand-400" />
                )}
              </button>
            )
          })}
        </div>
      </div>

      {/* Verified Toggle */}
      <div className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div
              className={`p-1 rounded ${
                filters.verified_only ? 'bg-success-500/20' : 'bg-gray-700/50'
              }`}
            >
              <Check
                className={`w-3.5 h-3.5 ${
                  filters.verified_only ? 'text-success-400' : 'text-gray-400'
                }`}
              />
            </div>
            <div>
              <span
                className={`text-xs ${
                  filters.verified_only
                    ? 'text-white font-medium'
                    : 'text-gray-400'
                }`}
              >
                Verified Only
              </span>
              <p className="text-[10px] text-gray-500">
                Show only tested templates
              </p>
            </div>
          </div>
          <Switch
            checked={filters.verified_only}
            onCheckedChange={handleVerifiedChange}
          />
        </div>
      </div>

      {/* Active Filters Summary */}
      {hasActiveFilters && (
        <div className="p-4 pt-0">
          <div className="p-2.5 rounded-lg bg-brand-500/5 border border-brand-500/10">
            <div className="flex flex-wrap gap-1.5">
              {filters.min_vram !== null && (
                <Badge variant="primary" className="text-[9px]">
                  <Cpu className="w-2.5 h-2.5 mr-1" />
                  {filters.min_vram}GB+
                </Badge>
              )}
              {filters.category !== null && (
                <Badge variant="primary" className="text-[9px]">
                  <Layers className="w-2.5 h-2.5 mr-1" />
                  {
                    CATEGORY_OPTIONS.find((c) => c.value === filters.category)
                      ?.label
                  }
                </Badge>
              )}
              {filters.verified_only && (
                <Badge variant="success" className="text-[9px]">
                  <Check className="w-2.5 h-2.5 mr-1" />
                  Verified
                </Badge>
              )}
            </div>
          </div>
        </div>
      )}
    </Card>
  )
}

export default TemplateFilters
